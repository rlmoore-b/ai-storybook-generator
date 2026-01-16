import os
import asyncio
import requests
from utils import acall_model, aclient
from prompts.image_prompts import *
# Ensure output directory exists
IMAGE_DIR = "generated_images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

# Global variable to store the "Revised Prompt" from the first generation
LOCKED_REVISED_PROMPT = None

async def get_consistency_guide(full_story_text):
    prompt = CONSISTENCY_GUIDE_PROMPT.format(full_story_text=full_story_text)
    print("Extracting character consistency details...")
    return await acall_model(prompt)

async def generate_image_prompt(paragraph, consistency_guide):
    prompt = IMAGE_SCENE_PROMPT.format(paragraph=paragraph, consistency_guide=consistency_guide)
    return await acall_model(prompt)

async def generate_dalle_image(image_prompt, index, story_folder):
    global LOCKED_REVISED_PROMPT
    
    print(f" [Img {index+1}] Requesting DALL-E 3...")

    # STRATEGY: 
    # If we have a locked revised prompt (from index 0), we append it 
    # to the current prompt to force the AI to use the exact same character details.
    final_prompt = image_prompt
    if index > 0 and LOCKED_REVISED_PROMPT:
        final_prompt = f"{image_prompt} . {LOCKED_REVISED_PROMPT}"

    try:
        response = await aclient.images.generate(
            model="dall-e-3",
            prompt=final_prompt,
            size="1024x1024",
            quality="standard",
            style="vivid",
            n=1
        )
        
        # CAPTURE STEP:
        # If this is the first image, save the revised prompt to use for all others
        if index == 0:
            LOCKED_REVISED_PROMPT = response.data[0].revised_prompt
            print(f" [Img 1] Character defined. Locked Prompt: {LOCKED_REVISED_PROMPT[:50]}...")

        image_url = response.data[0].url
        
        # Download and save locally to story-specific folder
        img_data = requests.get(image_url).content
        filename = f"{story_folder}/images/page_{index+1}.png"
        with open(filename, 'wb') as handler:
            handler.write(img_data)
        
        print(f" [Img {index+1}] Saved to {filename}")
        return filename
    except Exception as e:
        print(f"Error generating image {index+1}: {e}")
        return None

async def process_paragraph(index, paragraph, consistency_guide, story_folder):
    """
    Orchestrates the generation for a single paragraph: 
    Get Prompt -> Get Image -> Return Path
    """
    # 1. Generate the prompt
    dall_e_prompt = await generate_image_prompt(paragraph, consistency_guide)
    # 2. Generate the image
    img_path = await generate_dalle_image(dall_e_prompt, index, story_folder)
    return img_path

async def generate_story_images(story_text, story_folder):
    """
    Main entry point. Returns a list of image file paths (or None for failures).
    Takes story_folder as an argument to save images to the correct location.
    """
    # 1. Split story
    paragraphs = [p.strip() for p in story_text.split('\n') if p.strip()]
    if not paragraphs: 
        return []

    # 2. Get Guide
    guide = await get_consistency_guide(story_text)
    print(f"Consistency Guide: {guide}\n")

    # 3. Generate Image 1 FIRST (Blocking) to capture the Revised Prompt
    print(f"Generating first image to establish character consistency...")
    first_image_path = await process_paragraph(0, paragraphs[0], guide, story_folder)
    
    if not first_image_path:
        print("Failed to generate the first image. Aborting batch to save cost.")
        return []

    # 4. Create parallel tasks for the REMAINING paragraphs
    # Now that LOCKED_REVISED_PROMPT is set, these will use it.
    remaining_paragraphs = paragraphs[1:]
    
    if remaining_paragraphs:
        print(f"Starting parallel generation for remaining {len(remaining_paragraphs)} paragraphs...")
        tasks = []
        # Note: enumerate starts at 1 here to keep file naming consistent (page_2, page_3...)
        for i, p in enumerate(remaining_paragraphs, start=1):
            tasks.append(process_paragraph(i, p, guide, story_folder))

        # Wait for rest of images
        remaining_paths = await asyncio.gather(*tasks)
        all_paths = [first_image_path] + list(remaining_paths)
    else:
        all_paths = [first_image_path]
    
    print("All images generated.")
    return all_paths