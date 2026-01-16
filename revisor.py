from typing import Any, Dict, List, Tuple
from utils import call_model
from prompts.revisor_prompts import *

def _apply_patch_once(text: str, quote: str, fix: str) -> Tuple[str, bool]:
    """
    Replace the first occurrence of quote with fix.
    Returns (new_text, replaced_bool).
    """
    if not quote or quote not in text:
        return text, False
    return text.replace(quote, fix, 1), True

def _apply_patches_deterministically(story: str, patches: List[Dict[str, str]]) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Apply judge-provided patches (quote -> fix) in order.
    Returns revised_story and a patch report.
    """
    revised = story
    report: List[Dict[str, Any]] = []
    for p in patches:
        quote = (p.get("quote") or "").strip()
        fix = (p.get("fix") or "").strip()
        judge = (p.get("judge") or "").strip()
        reason = (p.get("reason") or "").strip()

        before = revised
        revised, ok = _apply_patch_once(revised, quote, fix)
        report.append({
            "judge": judge,
            "applied": ok,
            "reason": reason,
            "quote": quote,
            "fix": fix,
        })

    return revised, report

def _smoothing_pass(original_request: str, plan: str, story: str) -> str:
    """
    Lightweight coherence polish that should not rewrite the whole story.
    Keeps meaning + structure, removes awkward seams after patching.
    """
    prompt = STORY_SMOOTHER_PROMPT.format(original_request=original_request, plan=plan, story=story)
    return call_model(prompt, temperature=0.3, max_tokens=1800)

def revise_story(
    original_request: str,
    plan: str,
    current_story: str,
    judge_feedback: Dict[str, Any],
    do_smoothing_pass: bool = True
) -> str:
    """
    Evidence-anchored reviser.
    1) Applies judge 'patches' (quote->fix) deterministically.
    2) Optionally runs a small smoothing pass for coherence.
    """
    patches: List[Dict[str, str]] = judge_feedback.get("patches", []) or []

    print("  > Revising story based on evidence patches...")
    patched_story, patch_report = _apply_patches_deterministically(current_story, patches)

    # If many patches failed to apply (quotes missing), fall back to an LLM patcher
    failed = [r for r in patch_report if not r["applied"]]
    fail_rate = (len(failed) / max(1, len(patch_report))) if patch_report else 0.0

    if patches and fail_rate > 0.4:
        # Fallback: ask model to apply patches by meaning, but still anchored to the patch list
        patch_list_text = "\n".join(
            f"- QUOTE: {p['quote']}\n  FIX: {p['fix']}"
            for p in patches
            if p.get("quote") and p.get("fix")
        )

        prompt = STORY_REVISOR_PROMPT.format(original_request=original_request, plan=plan, story=current_story, patch_list_text=patch_list_text)
        patched_story = call_model(prompt, temperature=0.25, max_tokens=1800)

    # Optional: smooth seams after patching
    if do_smoothing_pass:
        patched_story = _smoothing_pass(original_request, plan, patched_story)

    return patched_story




def revise_brainstorm_ideas(
    original_request: str,
    brainstorm_text: str,
    judge_feedback: Dict[str, Any]
) -> str:
    """
    Evidence-anchored brainstorm revisor.
    Uses judge 'patches' (quote->fix) as constraints to rewrite the 3 ideas.
    Returns revised brainstorm list (3 numbered ideas).
    """
    patches: List[Dict[str, str]] = judge_feedback.get("patches", []) or []
    patch_list_text = "\n".join(
        f"- ISSUE QUOTE: {p.get('quote','')}\n  FIX: {p.get('fix','')}"
        for p in patches
        if p.get("quote") and p.get("fix")
    )

    prompt = BRAINSTORM_REVISOR_PROMPT.format(original_request=original_request, brainstorm_text=brainstorm_text, patch_list_text=patch_list_text)
    return call_model(prompt, temperature=0.9, max_tokens=900).strip()
