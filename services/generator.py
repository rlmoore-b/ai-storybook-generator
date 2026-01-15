"""
Story Generator Service

This module contains the core story generation pipeline that orchestrates
multiple AI agents to create high-quality children's stories.

Pipeline stages:
1. Input Sanitization - Content safety filtering
2. Brainstorming - Creative idea generation with quality loop
3. Story Planning - Narrative structure and character development
4. Story Writing - Full story composition
5. Quality Refinement - Multi-agent judging and revision loop (up to 10 iterations)
6. Asset Generation - Audio narration and illustrations (optional)

The generator uses a multi-agent system where:
- Different LLM calls handle different creative tasks
- Judge agents evaluate quality across multiple dimensions
- Revisor agents improve the story based on critiques
- The system iterates until quality thresholds are met

DEBUGGING CONTROLS:
- Set ENABLE_AUDIO = True/False to toggle audio narration
- Set ENABLE_IMAGES = True/False to toggle image generation
- Both flags below control expensive/time-consuming features

Author: Robert Moore
Date: January 2026
"""

import os
import asyncio
import requests
import uuid
from utils import call_model
from judge import comprehensive_judge, brainstorm_comprehensive_judge
from revisor import revise_story, revise_brainstorm_ideas
from storybook import generate_story_images

# ============================================
# DEBUG FLAGS - Toggle features on/off
# ============================================
# These flags allow you to test the story generation pipeline quickly
# without waiting for audio/image generation during development
ENABLE_AUDIO = True       # Set to True to generate audio narration (adds ~30-60s, costs ~$0.03)
ENABLE_IMAGES = True      # Set to True to generate story images (adds ~2-3 min, costs ~$0.40)
# ============================================

class StoryGenerator:
    """
    Multi-agent AI system for generating children's stories.
    
    This class orchestrates a complex pipeline of AI agents that work together
    to create high-quality, age-appropriate stories. The pipeline includes:
    - Input sanitization for safety
    - Creative brainstorming with quality control
    - Structured story planning
    - Story composition with specific style guidelines
    - Multi-dimensional quality judging
    - Iterative revision based on critiques
    - Optional multimedia generation (audio, images)
    
    The generator creates a unique folder for each story to store all
    associated assets (images, audio) for later retrieval.
    
    Attributes:
        execution_log (list): Running log of all generation steps
        story_uuid (str): Unique identifier for this story
        story_folder (str): Path to story's asset folder
    """
    
    def __init__(self, story_uuid=None):
        """
        Initialize a new story generator instance.
        
        Args:
            story_uuid (str, optional): Specific UUID to use. If None, generates a new one.
        """
        self.execution_log = []
        self.story_uuid = story_uuid or str(uuid.uuid4())
        self.story_folder = f'static/stories/{self.story_uuid}'
        
        # Create directory structure for this story's assets
        os.makedirs(self.story_folder, exist_ok=True)
        os.makedirs(f'{self.story_folder}/images', exist_ok=True)
        os.makedirs(f'{self.story_folder}/audio', exist_ok=True)
    
    def _log(self, message: str):
        """
        Log a message to both console and internal log.
        
        Args:
            message (str): Message to log
        """
        print(message)  # Print to server logs for monitoring
        self.execution_log.append(message)  # Store for returning to caller
    
    def sanitize_input(self, user_input: str) -> str:
        """
        Content safety filter - the first line of defense.
        
        Uses an LLM to detect and rewrite inappropriate content before it
        enters the story generation pipeline. This prevents generating stories
        about violence, mature themes, or other content unsuitable for children ages 5-10.
        
        If input is safe: Returns it unchanged
        If input is unsafe: Rewrites it into an age-appropriate metaphor
        
        Examples:
        - "War" → "A disagreement between groups learning to share"
        - "Guns" → "Magic wands that shoot sparkles"
        
        Args:
            user_input (str): Raw user prompt
            
        Returns:
            str: Sanitized prompt safe for children
        """
        sanitizer_prompt = f"""
            SYSTEM ROLE: You are a strict Safety Filter for a children's story generator (Ages 5-10).
            
            INPUT: "{user_input}"
            
            TASK:
            1. Analyze the input for prohibited content:
               - Violence or Weapons (guns, knives, bombs, murder, shooting).
               - Historical Tragedies, Politics, or Hate Speech (genocide, war, racism).
               - Sexual content, Drugs, or Alcohol.
               - Scary Horror or Nightmare themes.
               - Real historical tragedies or disasters.
               - Religion or belief systems.
               - Public figures, politicians, or celebrities
            
            2. DECISION:
               - IF SAFE: Return the input exactly as is.
               - IF UNSAFE: Rewrite the concept into a SAFE, AGE-APPROPRIATE METAPHOR.
                 - "War/Genocide" -> "A disagreement between two groups of forest animals trying to learn to share."
                 - "Guns/Weapons" -> "Magic wands that shoot sparkles or a beam of light."
                 - "Drugs/Alcohol" -> "A mysterious sleepy potion or sour tea."
                 - "Murder/Death" -> "Being trapped in a deep sleep or sent to the time-out corner."
                 - "public figures/politics" -> "Someone who is very popular."
            
            OUTPUT FORMAT:
            Return ONLY the cleaned text string. Do not add labels like "Sanitized:".
            """
        return call_model(sanitizer_prompt, temperature=0.0, max_tokens=1000).strip()
    
    def brainstorm_ideas(self, user_input: str) -> str:
        """
        Generate creative story concepts (Agent 2: Brainstormer).
        
        Takes the sanitized input and generates 3 unique, creative story hooks
        that go beyond obvious interpretations. Uses high temperature (1.5)
        for maximum creativity.
        
        Args:
            user_input (str): Sanitized story prompt
            
        Returns:
            str: 3 numbered creative story concepts
        """
        brainstorm_prompt = f"""
            SYSTEM ROLE: You are an avant-garde surrealist.
            TASK: The user wants a story about: "{user_input}".

            Generate 3 distinct, creative, and unusual concept hooks or plot twists for this topic. 
            - Go beyond the obvious.
            - Mix genres.
            - Focus on unique sensory details or weird character traits.
            - Ensure that the story is appropriate for a child aged 5 to 10.
            - Do not use concepts that are highly abstract. 

            OUTPUT: Just the list of 3 ideas. Do not write the story.
            """
        return call_model(brainstorm_prompt, temperature=1.5)
    
    def plan_story(self, user_input: str, brainstorm_result: str) -> str:
        """
        Create detailed story blueprint (Agent 3: Planner).
        
        Selects the best brainstormed concept and creates a complete
        narrative plan including characters, setting, plot beats, and moral core.
        This structured plan guides the story writer.
        
        Args:
            user_input (str): Original sanitized prompt
            brainstorm_result (str): List of 3 brainstormed concepts
            
        Returns:
            str: Detailed story plan with character details, plot structure, and theme
        """
        planner_prompt = f"""
            SYSTEM ROLE: You are an expert Narrative Architect for children's literature (Ages 5-10).

            INPUT CONTEXT:
            1. User's Original Request: "{user_input}"
            2. Brainstormed Concept: 
            {brainstorm_result}

            TASK:
            Analyze the "Brainstormed Concept" provided above. 
            Select the most creative element (or combine two unique ideas) to construct a cohesive story blueprint. 
            Do NOT write the full story yet. Write the Plan.

            REQUIRED OUTPUT FORMAT:

            **1. Selected Concept:** [Which idea from the brainstorming list are you using? Why?]

            **2. The Characters:**
            - Protagonist: [Name, Species, and one specific 'Quirk' or 'Flaw']
            - Antagonist or Obstacle: [Who or what stands in the way?]

            **3. The Setting & Atmosphere:**
            - Location: [Describe the world]
            - Sensory Detail: [Name one specific SMELL or SOUND that pervades the story]

            **4. Plot Beat Sheet:**
            - Introduction: [Establish the normal world]
            - Inciting Incident: [What specific event forces the hero to act?]
            - Rising Action: [Describe one specific attempt the hero makes that FAILS]
            - Climax: [The highest point of tension]
            - Resolution: [How is the conflict resolved?]

            **5. The Moral Core:**
            [What is the lesson? (e.g., 'Honesty is hard but necessary')]

            **6. The "Winning Move" (The Climax Mechanic):**
            [What exact actions happened in the climax. describe every action by the antagonist and protagonist with imagery and detail.]
            """
        return call_model(planner_prompt, temperature=0.7)
    
    def write_story(self, user_input: str, plan: str) -> str:
        """
        Compose the full story (Agent 4: Writer).
        
        Writes a complete 700-1100 word children's story following the plan exactly.
        Uses specific style guidelines, concrete sensory details, and age-appropriate
        language. Temperature 0.4 for consistency with the plan.
        
        Args:
            user_input (str): Original prompt (for context)
            plan (str): Detailed story blueprint from planner
            
        Returns:
            str: Complete story with title
        """
        storytelling_prompt = f"""
            SYSTEM ROLE: You are an award-winning children's bedtime story author (Ages 5–10). You write playful, vivid, comforting stories with gentle humor and a clear emotional arc.
            
            INPUTS:
            1) User's Original Request:
            "{user_input}"
            
            2) Story Plan (MUST FOLLOW EXACTLY):
            {plan}
            
            TASK:
            Write the full story based on the Story Plan above.
            
            HARD RULES:
            - You MUST follow the plan's: Selected Concept, Characters (including quirks/flaws), Setting & Atmosphere (including the specific SMELL or SOUND), Plot Beat Sheet (in the same order), and Moral Core.
            - Keep it appropriate for ages 5–10: no gore, no cruelty, no mature themes, no romance, no swearing.
            - The obstacle can be spooky or intense, but it must feel safe overall and end reassuringly.
            - Use concrete sensory details and a few fun, unusual metaphors, but keep language simple and clear.
            - Keep character names consistent. Do not introduce more than 2 minor side characters.
            - Story length: 700–1100 words.
            - Do not summarize action. Do not say "They used a clever strategy." You must DESCRIBE the strategy step-by-step.
            - Do not use meta-labels. Never write "In the climax..." or "The moral is..." inside the story text.
            - You are forbidden from writing "they came up with a plan" or "they devised a strategy." You must describe the EXACT action they took (e.g., "Luna shouted the secret word," "The Inkrops threw glitter," etc.).
            - In Rising Action, the hero must try one clear action that FAILS and makes things worse.
            - Do not use abstract nouns (e.g., harmony, courage, unity, imagination) during the climax. Use only physical actions and objects.
            
            STYLE GUIDELINES:
            - Warm, whimsical tone; short-to-medium sentences; occasional gentle repetition for rhythm.
            - Include 2–4 lines of dialogue, clearly marked with quotes.
            - Include one silly-but-memorable recurring detail (a sound, a smell, a phrase, or an object) that ties back to the plan's sensory detail.
            
            OUTPUT FORMAT:
            - Title: (one line)
            - Story (plain text, no bullets, no headings)

            
            BEGIN THE STORY NOW.
            """
        return call_model(storytelling_prompt, temperature=0.4)
    
    def generate_audio_file(self, story_text: str, voice="alloy"):
        """
        Generate audio narration of the story using OpenAI TTS.
        
        Converts the full story text into spoken audio for an immersive
        reading experience. The audio file is saved to the story's folder.
        
        Args:
            story_text (str): Complete story text to narrate
            voice (str): OpenAI TTS voice name (default: "alloy")
            
        Returns:
            str: Path to generated MP3 file, or None if generation failed
        """
        api_key = os.getenv("OPENAI_API_KEY")
        url = "https://api.openai.com/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "tts-1",
            "input": story_text,
            "voice": voice
        }
        
        self._log(f"Generating audio with voice: {voice}...")
        response = requests.post(url, headers=headers, json=data)
        
        filename = f"{self.story_folder}/audio/story.mp3"
        
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
            self._log(f"Successfully saved audio to {filename}")
            return filename
        else:
            self._log(f"Error generating audio: {response.text}")
            return None
    
    def generate(self, user_prompt: str) -> dict:
        """
        Main story generation pipeline - orchestrates all agents.
        
        This is the primary method that runs the complete multi-stage pipeline:
        1. Sanitize input for safety
        2. Brainstorm creative concepts (with quality loop)
        3. Plan narrative structure
        4. Write complete story
        5. Judge and revise (up to 10 iterations)
        6. Generate audio narration (if enabled)
        7. Generate illustrations (if enabled)
        
        The process takes 30 seconds to 5 minutes depending on enabled features.
        
        Args:
            user_prompt (str): Raw user input describing desired story
            
        Returns:
            dict: Story generation result containing:
                - success (bool): Whether generation succeeded
                - story_uuid (str): Unique story identifier
                - execution_log (list): Step-by-step log messages
                - story_text (str): Complete story with title
                - audio_path (str|None): Path to audio file
                - image_paths (list): Paths to generated images
                - title (str): Extracted story title
                - story_body (str): Story text without title
                - error (str): Error message if success=False
        """
        self.execution_log = []
        
        try:
            # 1. Upstream Sanitization
            self._log(" Sanitizing Input...")
            sanitized_input = self.sanitize_input(user_prompt)
            
            # 2. Brainstorming
            self._log(" Brainstorming Ideas...")
            brainstorm_result = self.brainstorm_ideas(sanitized_input)
            
            # 2.5. Brainstorm Judge-Revise Loop
            self._log("\n Brainstorm Judge-Revise Loop...")
            for r in range(5):
                verdict_b = asyncio.run(brainstorm_comprehensive_judge(brainstorm_result))
                self._log(f"Brainstorm Round {r+1}: Avg {verdict_b['average_score']:.2f} | Passed: {verdict_b['pass']}")
                d = verdict_b["details"]
                self._log(f"   Safety: {d['brainstorm_safety'].get('score')}/5")
                self._log(f"   Concrete: {d['brainstorm_concreteness'].get('score')}/5")
                self._log(f"   Unique: {d['brainstorm_uniqueness'].get('score')}/5")
                self._log(f"   Sensory: {d['brainstorm_sensory'].get('score')}/5")
                
                if verdict_b["pass"]:
                    break
                brainstorm_result = revise_brainstorm_ideas(sanitized_input, brainstorm_result, verdict_b)
            
            self._log(f" Brainstorm Final: {brainstorm_result}")


            # 3. Story Planning
            self._log(" Planning Story...")
            plan_response = self.plan_story(sanitized_input, brainstorm_result)
            
            # 4. Story Writing (Draft 1)
            self._log(" Writing Draft 1...")
            story = self.write_story(sanitized_input, plan_response)
            self._log(f"--- DRAFT 1 PREVIEW ---\n{story[:200]}...")
            
            # 5. Refinement Loop
            self._log(" Entering Judge-Revise Loop...")
            max_iterations = 10
            final_story = story
            
            for i in range(max_iterations):
                self._log(f"\n=== ROUND {i+1} EVALUATION ===")
                
                # Call the aggregated judge (async)
                verdict = asyncio.run(comprehensive_judge(story))
                
                # Log results
                round_log = f"Round {i+1}: Avg Score {verdict['average_score']:.1f} | Passed: {verdict['pass']}"
                self._log(round_log)
                
                # Display breakdown
                details = verdict['details']
                self._log(f"   Safety: {details['safety'].get('score')}/5")
                self._log(f"   Logic:  {details['comprehensibility'].get('score')}/5")
                self._log(f"   Writing:{details['writing'].get('score')}/5")
                self._log(f"   Theme:  {details['thematic'].get('score')}/5")
                
                if verdict["pass"]:
                    self._log("\n*** ALL JUDGES SATISFIED ***")
                    final_story = story
                    break
                else:
                    self._log("\n--- Critiques Received. Revising... ---")
                    story = revise_story(sanitized_input, plan_response, story, verdict)
                    final_story = story
                    
                    if i == max_iterations - 1:
                        self._log("Max iterations reached. Proceeding with current version.")
            
            # 6. Audio generation (optional)
            audio_path = None
            if ENABLE_AUDIO:
                self._log("\n Creating Audio Experience...")
                audio_path = self.generate_audio_file(final_story)
            else:
                self._log("\n[Audio generation DISABLED - skipping]")
            
            # 7. Generate Images (Parallelized)
            image_paths = []
            if ENABLE_IMAGES:
                self._log("\nGenerating Story Images (Parallel)...")
                image_paths = asyncio.run(generate_story_images(final_story, self.story_folder))
            else:
                self._log("\n[Image generation DISABLED - skipping]")
            
            # Parse title and body
            import re
            match = re.match(r"Title:\s*(.+?)\n\s*\n(.*)", final_story, re.DOTALL)
            if match:
                title = match.group(1).strip()
                story_body = match.group(2)
            else:
                lines = final_story.split('\n')
                title = lines[0] if lines else "My Story"
                story_body = "\n".join(lines[1:]) if len(lines) > 1 else final_story
            
            return {
                "success": True,
                "story_uuid": self.story_uuid,
                "execution_log": self.execution_log,
                "story_text": final_story,
                "audio_path": audio_path,
                "image_paths": image_paths,
                "title": title,
                "story_body": story_body
            }
        
        except Exception as e:
            self._log(f"ERROR: {str(e)}")
            return {
                "success": False,
                "execution_log": self.execution_log,
                "error": str(e)
            }
