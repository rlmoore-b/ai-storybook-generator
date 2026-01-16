"""
Interview Prompt Templates

Contains prompts for the audio interview feature that personalizes stories
through interactive voice Q&A.

Interview Agents:
- Question Generator: Creates 2 contextual follow-up questions based on story idea
- Prompt Synthesizer: Combines original idea + Q&A answers into enhanced prompt

The interview flow:
1. User provides basic story idea
2. Question Generator creates 2 relevant questions
3. Questions are spoken via OpenAI TTS
4. User answers via voice (transcribed by Whisper)
5. Prompt Synthesizer creates enhanced story prompt with all details

All prompts use {variable} placeholders for .format() substitution.
"""


INTERVIEW_QUESTION_GENERATOR_PROMPT = """
    A child wants to hear a story about: "{sanitized_prompt}"
    
    Generate exactly 2 short, friendly follow-up questions to personalize this story.
    
    Guidelines:
    - Ask about character details (names, colors, personality traits)
    - Ask about setting or plot details (where, when, what happens)
    - Use simple, warm language suitable for ages 5-10
    - Keep each question under 12 words
    - Make them open-ended but easy to answer
    - Be specific to their story idea
    
    Format your response as:
    1. [First question]
    2. [Second question]
    
    Example:
    Story: "A brave dragon learning to fly"
    1. What color should the dragon be?
    2. Who helps the dragon learn to fly?
    
    Now generate 2 questions for: "{sanitized_prompt}"
    """

INTERVIEW_PROMPT_SYNTHESIZER_PROMPT = """
    Original story idea: "{original_prompt}"
    
    Additional details from conversation:
    {qa_text}
    
    Rewrite this into a single, rich story prompt that naturally incorporates 
    all the details the child provided. Keep their original idea central, but 
    weave in the new information smoothly.
    
    Example:
    Original: "A dragon learning to fly"
    Details: 
    - What color? → Purple with sparkles
    - Who helps? → A wise owl named Oliver
    Enhanced: "A story about a magnificent purple dragon with sparkles on her 
    wings who is learning to fly, with help from her wise friend Oliver the owl"
    
    Write the enhanced prompt in 1-2 sentences:
    """


