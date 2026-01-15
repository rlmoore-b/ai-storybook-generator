from typing import Any, Dict, List, Tuple
from utils import call_model

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
    prompt = f"""
SYSTEM ROLE: You are a careful line editor for a children's bedtime story (Ages 5-10).

CONTEXT:
- User request: "{original_request}"
- Plan (must remain followed): {plan}

TASK:
Polish the story for flow AFTER small edits were applied:
- Do NOT change the plot.
- Do NOT add new characters.
- Do NOT add new major events.
- Do NOT remove key events.
- Only smooth transitions, fix pronouns, and reduce repetition.
- Keep it age-appropriate and comforting.
- Keep length roughly the same (700-1100 words).

OUTPUT:
Return ONLY the full story (Title + Body).

STORY:
{story}
"""
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

        prompt = f"""
SYSTEM ROLE: You are an Expert Story Editor. You must apply requested fixes with minimal change.

CONTEXT:
- User request: "{original_request}"
- Plan (must remain followed): {plan}

CURRENT STORY:
{current_story}

PATCHES TO APPLY (anchor to these):
{patch_list_text}

TASK:
Rewrite the story by applying the PATCHES above.
Rules:
- Make the smallest possible edits.
- Keep plot, characters, and events the same.
- Keep it safe and age-appropriate (5-10).
- Keep length roughly the same (700-1100 words).
- Do not introduce new themes unrelated to the plan.

OUTPUT:
Return ONLY the full revised story (Title + Body).
"""
        #patched_story = call_model(prompt, temperature=0.25, max_tokens=1800)
        patched_story = call_model(prompt, temperature=0.25, max_tokens=1800)

    # Optional: smooth seams after patching
    if do_smoothing_pass:
        print("Story before smoothing: ", patched_story)
        patched_story = _smoothing_pass(original_request, plan, patched_story)
        print("Story after smoothing: ", patched_story)

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

    prompt = f"""
SYSTEM ROLE: You are an expert children's story ideation editor.

USER REQUEST:
"{original_request}"

CURRENT BRAINSTORM (3 ideas):
{brainstorm_text}

JUDGE PATCHES (apply these):
{patch_list_text}

TASK:
Rewrite the brainstorm into EXACTLY 3 ideas that:
- stay on-topic for the user's request
- are safe for ages 5–10 (kid-safe tension OK)
- are CONCRETE: each idea must include
  (1) a PHYSICAL OBJECT stake
  (2) a PHYSICAL MECHANISM
  (3) a MEASURABLE GOAL / TIMER (collect X, fix Y, before Z)
- are UNIQUE: avoid cliché hooks (portals/enchanted forests/generic shadow villains) unless twisted into something truly new
- are VIVID: include at least one specific sensory detail (sound OR smell OR touch OR visual texture) per idea
- do NOT use highly abstract stakes ("steal happiness", "darkness grows") unless converted into physical objects and actions
- are specific enough that a child could act them out

OUTPUT RULES:
- Output ONLY the revised list of 3 ideas.
- Number them 1–3.
- Each idea should be 2–4 sentences max.
- Do NOT write a full story.

REVISED 3 IDEAS:
"""
    return call_model(prompt, temperature=0.9, max_tokens=900).strip()
