"""
Image Generation Prompt Templates

Contains prompts for the DALL-E 3 image generation system that creates
character-consistent storybook illustrations.

Image Generation Agents:
- Consistency Analyzer: Extracts character/style guide from full story
- Scene Prompter: Converts each paragraph into detailed DALL-E prompts

The image generation uses a 3-agent system:
1. Consistency Analyzer reads the full story once
2. First image is generated (DALL-E's revised prompt is locked for consistency)
3. Scene Prompter creates prompts for remaining paragraphs
4. All remaining images generated in parallel with locked character details

This ensures characters look identical across all 8-12 illustrations.

All prompts use {variable} placeholders for .format() substitution.
"""

# Character Consistency
# =====================

CONSISTENCY_GUIDE_PROMPT =  """
        Read the following story and create a visual 'System Prompt' for an image generator. 
        Describe the physical appearance of the main characters (hair, clothes, age, race), the setting, and the artistic style (e.g., watercolor, 3D render, cartoon). 
        Keep it concise (under 50 words). 
        
        Story:
        {full_story_text}
    """


# Scene Prompting
# ===============

IMAGE_SCENE_PROMPT = """
    I need a prompt for DALL-E 3 to generate an image for a storybook.

    Consistency Guide (Always follow this): 
    {consistency_guide}

    Current Scene Action: 
    {paragraph}

    Write a descriptive image prompt that depicts this scene using the style and characters from the consistency guide. Focus on lighting and composition.
    """
