import json
import asyncio
from typing import Any, Dict, List
from utils import call_model
from prompts.judge_prompts import *

# -------------------------
# Common JSON parsing utils
# -------------------------

DEFAULT_JUDGE_RESPONSE = {
    "score": 1,
    "metrics": {},
    "critique": "Error: Judge failed to produce valid JSON.",
    "violations": [],
}

def _extract_json_object(text: str) -> str:
    """Extract the first top-level JSON object from a messy LLM response."""
    cleaned = text.strip().replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        return cleaned[start:end + 1]
    return cleaned

def parse_judge_response(response_text: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Parses the JSON response from the judges.
    Handles markdown fencing and common model failure modes.
    """
    if default is None:
        default = dict(DEFAULT_JUDGE_RESPONSE)

    try:
        obj_text = _extract_json_object(response_text)
        data = json.loads(obj_text)

        # Ensure keys exist
        data.setdefault("score", 1)
        data.setdefault("metrics", {})
        data.setdefault("critique", "")
        data.setdefault("violations", [])

        # Normalize violations
        if not isinstance(data["violations"], list):
            data["violations"] = []

        # Normalize each violation shape
        norm_violations = []
        for v in data["violations"]:
            if isinstance(v, dict):
                norm_violations.append({
                    "quote": str(v.get("quote", "")).strip(),
                    "reason": str(v.get("reason", "")).strip(),
                    "fix": str(v.get("fix", "")).strip(),
                })
        data["violations"] = norm_violations
        return data
    except Exception:
        return dict(default)

# -------------------------
# Judges (evidence-based)
# -------------------------

async def safety_judge(story: str) -> Dict[str, Any]:
    prompt = SAFETY_JUDGE_PROMPT.format(story=story)
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)

async def comprehensibility_judge(story: str) -> Dict[str, Any]:
    prompt = COMPREHENSIBILITY_JUDGE_PROMPT.format(story=story)
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)

async def writing_quality_judge(story: str) -> Dict[str, Any]:
    prompt = WRITING_QUALITY_JUDGE_PROMPT.format(story=story)
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)

async def thematic_judge(story: str) -> Dict[str, Any]:
    prompt = THEMATIC_JUDGE_PROMPT.format(story=story)
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


# -------------------------
# Aggregation + patch list
# -------------------------

def collect_all_patches(details: Dict[str, Dict[str, Any]]) -> List[Dict[str, str]]:
    patches: List[Dict[str, str]] = []
    for judge_name, res in details.items():
        for v in res.get("violations", []) or []:
            quote = (v.get("quote") or "").strip()
            fix = (v.get("fix") or "").strip()
            reason = (v.get("reason") or "").strip()
            if quote and fix:
                patches.append({
                    "judge": judge_name,
                    "quote": quote,
                    "reason": reason,
                    "fix": fix,
                })
    return patches

async def comprehensive_judge(story: str) -> Dict[str, Any]:
    print("  > Running judges in parallel...")
    s_res, c_res, w_res, t_res = await asyncio.gather(
    safety_judge(story),
    comprehensibility_judge(story),
    writing_quality_judge(story),
    thematic_judge(story),
    )

    details = {
        "safety": s_res,
        "comprehensibility": c_res,
        "writing": w_res,
        "thematic": t_res
    }

   # --- Scores ---
    s_score = int(s_res.get("score", 1))
    c_score = int(c_res.get("score", 1))
    w_score = int(w_res.get("score", 1))
    t_score = int(t_res.get("score", 1))

    scores = [s_score, c_score, w_score, t_score]
    avg_score = sum(scores) / len(scores)

    # --- PASS RULE ---
    # Safety must be 5, others must be >= 4
    all_pass = (
        s_score == 5 and
        c_score >= 4 and
        w_score >= 4 and
        t_score >= 4
    )

    patches = collect_all_patches(details)

    patches = [
        p for p in patches
        if p.get("fix") and p.get("quote")
        and p["fix"].strip() != p["quote"].strip()
    ]

    collective_critique = (
        f"SAFETY (Score {s_res.get('score')}): {s_res.get('critique')}\n"
        f"LOGIC (Score {c_res.get('score')}): {c_res.get('critique')}\n"
        f"WRITING (Score {w_res.get('score')}): {w_res.get('critique')}\n"
        f"THEME (Score {t_res.get('score')}): {t_res.get('critique')}"
    )

    return {
        "pass": all_pass,
        "average_score": avg_score,
        "details": details,
        "patches": patches,
        "collective_critique": collective_critique
    }


# ============================================================
# Brainstorm Phase Judges (ideas-only, not full story)
# ============================================================

async def brainstorm_concreteness_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Checks that each brainstormed idea is concrete (objects + mechanisms + measurable stakes),
    and avoids nebulous abstract stakes ("steal happiness", "darkness grows") without physical mechanics.
    """
    prompt = BRAINSTORM_CONCRETENESS_JUDGE_PROMPT.format(brainstorm=brainstorm)
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_uniqueness_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Scores originality of brainstorm ideas. Penalizes clichés and generic premises.
    Requires a fresh rule/constraint/quirk that differentiates the idea.
    """
    prompt = BRAINSTORM_UNIQUENESS_JUDGE_PROMPT.format(brainstorm=brainstorm)
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_sensory_details_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Ensures each idea contains vivid, specific sensory anchors (sound/smell/touch/visual texture),
    not vague words like "beautiful" or "colorful".
    """
    prompt = BRAINSTORM_SENSORY_JUDGE_PROMPT.format(brainstorm=brainstorm)
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_safety_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Safety judge for brainstorm ideas (not full story). Allows kid-safe tension but flags
    horror, cruelty, weapons, death, hate, sexual content, drugs/alcohol, etc.
    Also flags 'too scary' antagonists (demon, monster eating people) unless softened.
    """
    prompt = BRAINSTORM_SAFETY_JUDGE_PROMPT.format(brainstorm=brainstorm)
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_comprehensive_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Runs all 4 brainstorm judges in parallel. Pass condition:
    - safety >= 4 (allow minor softening)
    - concreteness >= 4
    - uniqueness >= 3
    - sensory >= 4
    """
    print("  > Running brainstorm judges in parallel...")
    conc_res, uniq_res, sens_res, safe_res = await asyncio.gather(
        brainstorm_concreteness_judge(brainstorm),
        brainstorm_uniqueness_judge(brainstorm),
        brainstorm_sensory_details_judge(brainstorm),
        brainstorm_safety_judge(brainstorm),
    )

    details = {
        "brainstorm_concreteness": conc_res,
        "brainstorm_uniqueness": uniq_res,
        "brainstorm_sensory": sens_res,
        "brainstorm_safety": safe_res,
    }

    conc_score = int(conc_res.get("score", 1))
    uniq_score = int(uniq_res.get("score", 1))
    sens_score = int(sens_res.get("score", 1))
    safe_score = int(safe_res.get("score", 1))

    scores = [conc_score, uniq_score, sens_score, safe_score]
    avg_score = sum(scores) / len(scores)

    all_pass = (
        safe_score >= 4 and
        conc_score >= 4 and
        uniq_score >= 3 and
        sens_score >= 4
    )

    patches = collect_all_patches(details)
    patches = [
        p for p in patches
        if p.get("fix") and p.get("quote")
        and p["fix"].strip() != p["quote"].strip()
    ]

    collective_critique = (
        f"SAFETY ({safe_score}/5): {safe_res.get('critique')}\n"
        f"CONCRETENESS ({conc_score}/5): {conc_res.get('critique')}\n"
        f"UNIQUENESS ({uniq_score}/5): {uniq_res.get('critique')}\n"
        f"SENSORY ({sens_score}/5): {sens_res.get('critique')}"
    )

    return {
        "pass": all_pass,
        "average_score": avg_score,
        "details": details,
        "patches": patches,
        "collective_critique": collective_critique
    }
