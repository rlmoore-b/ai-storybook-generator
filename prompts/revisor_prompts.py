"""
Revisor Prompt Templates

Contains prompts for revision agents that improve content based on judge feedback.

Revisors:
- Story Revisor: Fixes issues in complete stories
- Brainstorm Revisor: Improves brainstorm ideas

All prompts use {variable} placeholders for .format() substitution.
"""

# Story Revisor
# =============

STORY_REVISOR_PROMPT = """
SYSTEM ROLE: You are an Expert Story Editor. You must apply requested fixes with minimal change.

CONTEXT:
- User request: "{original_request}"
- Plan (must remain followed): {plan}

CURRENT STORY:
{story}

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

STORY_SMOOTHER_PROMPT = """
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


# Brainstorm Revisor
# ==================

BRAINSTORM_REVISOR_PROMPT = """
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
