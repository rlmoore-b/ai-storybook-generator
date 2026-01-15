import json
import asyncio
from typing import Any, Dict, List
from utils import call_model

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
    prompt = f"""
SYSTEM ROLE: You are a Safety Compliance Officer for children's content (Ages 5-10).

GOAL: Identify unsafe, intense, or age-inappropriate elements.

RUBRIC:
- 5: Perfectly safe. Minor tension but still gentle.
- 4: Complex words being used.
- 3: Mildly spooky/intense language not quickly resolved.
- 2: Violence/weapons/bullying language (even if not graphic).
- 1: Explicitly unsafe (gore, death, hate, sex).

INSTRUCTIONS (IMPORTANT):
- You MUST cite evidence by quoting the exact offending text.
- Each "quote" must be copied verbatim from the story.
- If there are no issues, violations MUST be an empty list.
- Keep quotes short (1 sentence or fragment) but exact.

Return JSON ONLY in this schema:
{{
  "score": <1-5>,
  "metrics": {{
    "unsafe_items": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim excerpt from story>",
      "reason": "<why it violates safety>",
      "fix": "<how to rewrite safely without changing meaning>"
    }}
  ]
}}

STORY:
{story}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)
    #return parse_judge_response(call_model(prompt, temperature=0.0), default=DEFAULT_JUDGE_RESPONSE)

async def comprehensibility_judge(story: str) -> Dict[str, Any]:
    prompt = f"""
SYSTEM ROLE: You are a Logic and Flow Editor.

GOAL: Find confusing jumps, unclear pronouns, missing causes, continuity issues.

RUBRIC:
- 5: Crystal clear logic.
- 4: Mostly clear, one minor confusion.
- 3: Some jumps or unclear transitions.
- 2: Hard to follow.
- 1: Incoherent.

INSTRUCTIONS:
- Quote EXACT confusing lines (verbatim).
- Suggest a concrete fix (rewrite that line OR add a bridging sentence).
- If there are no issues, violations MUST be an empty list.

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "logic_issues": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim confusing excerpt>",
      "reason": "<what is unclear>",
      "fix": "<rewrite or bridging sentence to add>"
    }}
  ]
}}

STORY:
{story}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)
    #return parse_judge_response(call_model(prompt, temperature=0.0), default=DEFAULT_JUDGE_RESPONSE)

async def writing_quality_judge(story: str) -> Dict[str, Any]:
    prompt = f"""
SYSTEM ROLE: You are a strict "Show, Don't Tell" Writing Coach for children's stories (Ages 5–10).

PRIMARY GOAL:
Find the highest-impact "telling" sentences and propose PATCHES that can be safely applied using simple string replacement.

CRITICAL PATCH COMPATIBILITY (HARD RULES):
- Each violation "quote" MUST be a FULL sentence copied VERBATIM from the story.
- Each violation "fix" MUST be a REPLACEMENT that can substitute for the quote with minimal ripple effects.
- Therefore: each "fix" must be EXACTLY 1 sentence (preferred) or 2 sentences max.
- Do NOT add new characters, new locations, or new major events. Keep plot identical.
- Do NOT repeat the same idea twice. Your fix should replace the telling sentence, not add another version of it.

WHAT COUNTS AS "TELLING" (flag these):
A) Emotion labels without observable evidence:
   - "He felt brave/sad/nervous/happy." "She was determined." "They were worried."
B) Abstract morals / preachy wrap-ups:
   - "This taught them that..." "They learned an important lesson..."
C) Vague or summarized action:
   - "They worked together." "He tried his best." "They came up with a plan."
D) Generic intensifiers / vague nouns:
   - "very," "really," "amazing," "incredible," "something strange," "mysterious force"
E) Strategy talk without concrete steps:
   - "He was clever." "She figured it out." "They knew what to do."

BANNED WORDS/PHRASES IN FIXES (DO NOT USE):
- felt, feeling, realized, learned, lesson, important, teamwork, brave, courage, determined, worried, panic, proud,
  in that moment, suddenly (unless absolutely necessary), as if, seemed to, began to, started to,
  "After feeling", "After realizing", "This taught", "They learned"

REQUIREMENTS FOR EACH FIX (HARD):
Your replacement sentence(s) MUST include:
1) One concrete physical action (grabbed, tucked, sniffed, tapped, stepped, tilted, yanked, peered, etc.)
AND
2) Either:
   - one sensory detail (sound/smell/touch/visual texture), OR
   - a short dialogue fragment in quotes, OR
   - a distinct sound effect word (clink, whoosh, plink, pop).
AND
3) Preserve specificity by reusing at least ONE existing noun from the story’s world
   (e.g., pendant, horn, lotus, pond, sprites, crystals, trap, market stall, etc.).
   Do NOT replace specific nouns with generic ones.

SELECTION INSTRUCTIONS:
1) Scan the story and list up to 10 telling sentences.
2) Choose the TOP 3–5 sentences whose replacement would improve the story the most.
   Prefer: inciting incident, first failure, climax, resolution.
3) For each chosen sentence, write a replacement that keeps meaning but SHOWS via action/sensory.

FEW-SHOT EXAMPLES (PATCH-SAFE):

Example 1
QUOTE: "Milo felt nervous as he approached the cave."
GOOD FIX (1 sentence): "Milo’s paws slid on the damp stones, and he whispered, 'One step,' while drip-drip echoes tapped the cave walls."

Example 2
QUOTE: "They learned that teamwork is important."
GOOD FIX (2 sentences max): "Tess held the map steady while Jun angled the lantern until the ink shone. 'You point—I'll light,' Jun said, and the hidden arrow finally appeared."

Example 3 (Vague strategy)
QUOTE: "She came up with a plan."
GOOD FIX (1 sentence): "She pinched the pendant between her claws, listened to the wind’s hiss, and murmured, 'Left at the banyan—then run.'"

SCORING RUBRIC (1–5):
- 5: Almost no telling; key moments shown with concrete actions and sensory anchors.
- 4: A few telling lines remain.
- 3: Several telling lines; key beats often summarized.
- 2: Mostly summary; few concrete scenes.
- 1: Pure summary.

OUTPUT RULES:
- Output JSON ONLY in the schema below.
- "violations" must be [] if there are no issues.
- "summary_sentences" should equal len(violations).
- "high_impact_fixes" should equal the number of fixes that target a major plot beat (usually the same as violations).

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "summary_sentences": <int>,
    "high_impact_fixes": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim telling sentence>",
      "reason": "<why it's telling + what must be shown instead>",
      "fix": "<1 sentence (or 2 max) patch-safe replacement>"
    }}
  ]
}}

STORY:
{story}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 3000, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)

async def thematic_judge(story: str) -> Dict[str, Any]:
    prompt = f"""
SYSTEM ROLE: You are a Creative Director and children's story editor (Ages 5–10).

GOAL:
Identify clichés, preachy lines, or generic theme moments, then propose specific line-level rewrites
that feel fresher WITHOUT changing the plot.

WHAT COUNTS AS CLICHÉ / GENERIC (flag these):
A) Moralizing wrap-ups:
   - "And that's when they learned..." "This taught them..." "The moral is..."
B) Generic virtues without action:
   - "be brave," "believe in yourself," "never give up," "follow your dreams"
C) Stock phrases:
   - "little did they know," "heart pounding," "all was well," "suddenly," "just in time"
D) Vague theme statements:
   - "true happiness comes from within," "they found courage," "they felt hope"
E) Generic villains/obstacles described as vibes:
   - "a mysterious force," "the darkness," "an evil shadow" (unless given a physical mechanic)

IMPORTANT:
Kid stories CAN be simple; do NOT flag simple language if it is concrete and specific.
We only flag lines that are interchangeable across many stories.

EVALUATION STEPS (do these internally):
1) Scan the story and list up to 8 candidate cliché/generic lines.
2) Choose the TOP 4 that are most damaging (usually: ending moral lines + generic turning points).
3) For each chosen line:
   - Quote it verbatim (must be exact text from story).
   - Explain why it’s generic (1 sentence).
   - Provide a replacement line that:
     * keeps the meaning and plot intact
     * adds a specific image, physical action, or distinctive detail
     * avoids preachy phrasing
     * is roughly similar length so it can be patched in

FEW-SHOT EXAMPLES:

Example 1 (Preachy moral -> fresher concrete beat)
QUOTE: "And that's when Mia learned that teamwork is important."
FIX: "Mia held the ladder steady while Bo tightened the last bolt—clink!—and the wobbly sign finally stood straight."

Example 2 (Generic courage -> concrete action)
QUOTE: "Leo felt brave and faced the darkness."
FIX: "Leo took one slow step forward, tapping the floor with his flashlight until it clicked on a hidden chalk arrow."

Example 3 (Stock phrase -> specific twist)
QUOTE: "Little did they know, a surprise was waiting."
FIX: "Behind the cookie jar, a tiny paper door fluttered open—pfft!—and warm cinnamon air spilled out."

RUBRIC (1–5):
- 5: Fresh + memorable; theme emerges through specific actions/images; minimal cliché phrasing.
- 4: Solid but standard; a few lines feel familiar.
- 3: Some clichés/generic theme lines that could fit many stories.
- 2: Very generic or preachy; theme stated directly instead of shown.
- 1: Unrelated or mostly cliché.

OUTPUT RULES:
- Each violation "quote" must be copied verbatim from the story.
- Each "fix" must be a direct replacement line (1–2 sentences max), not a whole paragraph rewrite.
- If there are no issues, violations MUST be [].

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "cliches": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim excerpt>",
      "reason": "<why cliché/generic>",
      "fix": "<specific replacement line(s) that is more original>"
    }}
  ]
}}

STORY:
{story}
"""
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
    prompt = f"""
SYSTEM ROLE: You are a strict Concreteness Judge for children's story BRAINSTORM IDEAS (Ages 5-10).

TASK:
Evaluate the brainstorm list of 3 ideas. Identify where ideas are too abstract or "vibes-only".
Provide evidence-based violations with specific fixes.

EVALUATION STEPS (do these internally):
1) Split the input into Idea 1, Idea 2, Idea 3.
2) For each idea, check for:
   A) PHYSICAL OBJECT stake (jar, marbles, bell, map, sticker, key, etc.)
   B) PHYSICAL MECHANISM (spills, melts, swaps, shrinks, tangles, floats away, etc.)
   C) MEASURABLE GOAL / TIMER (collect X, fix Y, before Z)
3) Flag any abstract stakes without a physical stand-in (e.g., "steals happiness", "consumes joy").
4) Produce violations with verbatim quotes + exact fix instructions.

RUBRIC (1-5):
- 5: All 3 ideas clearly include object + mechanism + measurable goal. No abstract stakes.
- 4: Mostly concrete; one minor missing piece (e.g., metric missing in 1 idea).
- 3: Mixed; multiple missing objects/mechanics/metrics or some abstract stakes.
- 2: Mostly abstract/vague.
- 1: Unusable: highly abstract, unclear, or non-observable stakes.

FEW-SHOT EXAMPLES:

Example A (BAD, abstract):
Input idea: "A shadow steals everyone's happiness."
Violation fix: Replace with physical: "A shadowy cloud vacuums giggle-bubbles from jars; the dog must collect 12 bubbles before sunset."

Example B (GOOD, concrete):
Input idea: "Every time the dog barks, a glitter-key appears. If it finds 7 keys before the clock chimes, it can unlock the stuck rainbow door."
No violation.

OUTPUT RULES:
- You MUST quote exact fragments from the brainstorm as evidence.
- Fixes must be specific (add object + mechanism + metric).
- If no issues, violations must be [].

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "abstract_issues": <int>,
    "missing_object": <int>,
    "missing_mechanism": <int>,
    "missing_metric": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim excerpt from brainstorm>",
      "reason": "<why it's too abstract / missing physicality>",
      "fix": "<exact rewrite instruction or replacement phrase>"
    }}
  ]
}}

BRAINSTORM:
{brainstorm}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_uniqueness_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Scores originality of brainstorm ideas. Penalizes clichés and generic premises.
    Requires a fresh rule/constraint/quirk that differentiates the idea.
    """
    prompt = f"""
SYSTEM ROLE: You are a ruthless Uniqueness Judge for children's story BRAINSTORM IDEAS (Ages 5-10).

TASK:
Judge how unique the 3 ideas are. Identify clichés/generic tropes and propose sharper twists.

EVALUATION STEPS (do these internally):
1) Split into 3 ideas.
2) For each idea, check:
   A) Is the core hook common? (portal, magic forest, generic villain, wish, "learns a lesson")
   B) Is there a DISTINCT rule of the world? (specific constraint that changes everything)
   C) Is there a surprising genre-mash that is still kid-safe?
3) Flag any idea that could be swapped into 1000 other stories with minimal changes.
4) Provide a fix: add one specific twist/constraint/quirk.

RUBRIC (1-5):
- 5: All 3 ideas feel fresh, specific, and hard to confuse with generic stories.
- 4: Mostly unique; 1 idea is familiar but has a solid twist.
- 3: Mixed; 2 ideas feel familiar/cliché.
- 2: Mostly generic; novelty is surface-level.
- 1: Extremely cliché/generic.

FEW-SHOT EXAMPLES:

Example A (GENERIC):
"Dog finds a magical portal to a secret land."
Fix: Add specific constraint: "The portal only opens when the dog sneezes; each sneeze swaps two objects in town."

Example B (UNIQUE):
"Dog joins a library where books bark back; every bark rearranges the words, creating a new map to follow."
No violation.

OUTPUT RULES:
- Quote exact cliché/generic phrases.
- Fix must be specific and small (change the hook, add a constraint).
- Do NOT write the story.

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "cliches": <int>,
    "generic_ideas": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim excerpt from brainstorm>",
      "reason": "<why it feels generic>",
      "fix": "<specific hook rewrite that adds uniqueness>"
    }}
  ]
}}

BRAINSTORM:
{brainstorm}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_sensory_details_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Ensures each idea contains vivid, specific sensory anchors (sound/smell/touch/visual texture),
    not vague words like "beautiful" or "colorful".
    """
    prompt = f"""
SYSTEM ROLE: You are a Sensory Details Judge for children's story BRAINSTORM IDEAS (Ages 5-10).

TASK:
Evaluate vividness. Make each idea easy to "see/hear/smell" with specific sensory anchors.

EVALUATION STEPS (do these internally):
1) Split into 3 ideas.
2) For each idea, check: does it include at least ONE specific sensory detail?
   - SOUND (e.g., "squeaky balloon", "clink-clink marbles", "whoosh of a vacuum cloud")
   - SMELL (e.g., "warm cinnamon", "wet fur", "fresh crayons")
   - TOUCH/TEXTURE (e.g., "sticky jelly", "cold metal", "fuzzy sweater")
   - VISUAL TEXTURE (e.g., "sparkly dust trail", "foggy glass", "striped shadows")
3) Flag:
   A) missing sensory detail
   B) vague sensory language ("beautiful", "nice smell", "loud noise")
   C) sensory detail that doesn't connect to the hook

RUBRIC (1-5):
- 5: Every idea has vivid, specific sensory anchors that fit the hook.
- 4: All ideas have sensory detail; 1 is slightly generic.
- 3: Only 1–2 ideas have vivid sensory anchors.
- 2: Mostly vague sensory language.
- 1: No sensory detail.

FEW-SHOT EXAMPLES:

Example A (VAGUE):
"Colorful magical garden."
Fix: "The garden smells like oranges, and the flowers make a tiny 'plink' sound when touched."

Example B (VIVID):
"The dog chases a cinnamon-scented bubble that squeaks like a toy when it pops."
No violation.

OUTPUT RULES:
- Quote the exact phrase that is vague/missing sensory detail.
- Fix must add ONE sensory anchor phrase and where to insert it.

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "ideas_missing_sensory": <int>,
    "vague_sensory_phrases": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim excerpt from brainstorm>",
      "reason": "<why not vivid enough>",
      "fix": "<specific sensory phrase + insertion guidance>"
    }}
  ]
}}

BRAINSTORM:
{brainstorm}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_safety_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Safety judge for brainstorm ideas (not full story). Allows kid-safe tension but flags
    horror, cruelty, weapons, death, hate, sexual content, drugs/alcohol, etc.
    Also flags 'too scary' antagonists (demon, monster eating people) unless softened.
    """
    prompt = f"""
SYSTEM ROLE: You are a Safety Compliance Officer for children's BRAINSTORM IDEAS (Ages 5-10).

TASK:
Evaluate safety of the ideas. Tension is allowed (kid-safe peril), but ideas must not be scary/inappropriate.

EVALUATION STEPS (do these internally):
1) Split into 3 ideas.
2) For each idea, check for prohibited content:
   - Weapons/violence (guns, knives, killing, blood, gore)
   - Death, murder, suicide, torture
   - Hate speech, racism, politics, real-world tragedies
   - Sexual content, romance themes beyond innocent kid stuff
   - Drugs, alcohol
   - Horror imagery too intense for 5-10 (demons, possession, graphic monsters)
3) Also check "scariness level":
   - Allowed: silly spooky, mild suspense, a grumpy storm cloud, a mischievous shadow that steals socks.
   - Not allowed: nightmares, threats of death, kidnapping, dismemberment, realistic injury.
4) Provide fixes that preserve tension but make it kid-safe (swap to goofy stakes, soften language, make antagonist comical).

RUBRIC (1-5):
- 5: Perfectly safe; gentle tension only.
- 4: Safe but slightly intense wording; needs minor softening.
- 3: Noticeably spooky/scary elements; could scare younger kids.
- 2: Inappropriate elements (violence/weapons/bullying) even if not graphic.
- 1: Explicitly unsafe content (gore, death, hate, sex, drugs).

FEW-SHOT EXAMPLES:

Example A (TOO SCARY):
"A demon drags the dog into the underworld."
Fix: "A grumpy raincloud blows the dog into a bouncy pillow-cave; it must find 5 squeaky exits."

Example B (SAFE TENSION):
"A storm cloud steals the town's balloon-laughs and the dog must pop the right cloud-bubble before bedtime."
No violation.

OUTPUT RULES:
- Quote exact unsafe/scary phrases.
- Fix must keep the core hook but make it age-appropriate.

Return JSON ONLY:
{{
  "score": <1-5>,
  "metrics": {{
    "unsafe_items": <int>,
    "too_scary_items": <int>
  }},
  "critique": "<1-2 sentences>",
  "violations": [
    {{
      "quote": "<verbatim excerpt from brainstorm>",
      "reason": "<why unsafe/too scary>",
      "fix": "<kid-safe rewrite that preserves tension>"
    }}
  ]
}}

BRAINSTORM:
{brainstorm}
"""
    resp_text = await asyncio.to_thread(call_model, prompt, 1100, 0.0)
    return parse_judge_response(resp_text, default=DEFAULT_JUDGE_RESPONSE)


async def brainstorm_comprehensive_judge(brainstorm: str) -> Dict[str, Any]:
    """
    Runs all 4 brainstorm judges in parallel. Pass condition:
    - safety >= 4 (allow minor softening)
    - concreteness >= 4
    - uniqueness >= 4
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
        uniq_score >= 4 and
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
