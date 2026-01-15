"""
Interactive Story Interview Service

This module implements an audio-based interview system that personalizes
stories through natural voice interaction. It's designed to make story
creation more engaging, especially for children.

The interview process:
1. Generates contextual questions based on the user's initial story idea
2. Converts questions to speech using OpenAI TTS (Text-to-Speech)
3. Records user's voice answers
4. Transcribes answers using OpenAI Whisper (Speech-to-Text)
5. Synthesizes an enhanced story prompt incorporating all details

All audio processing uses OpenAI APIs, requiring only an OPENAI_API_KEY.

Example flow:
    User: "A dragon learning to fly"
    Q1 (audio): "What color should the dragon be?"
    A1 (voice): "Purple with sparkles"
    Q2 (audio): "Who helps the dragon learn?"
    A2 (voice): "A wise owl named Oliver"
    Enhanced: "A purple dragon with sparkles learning to fly with owl Oliver"

Author: Robert Moore
Date: January 2026
"""

import os
from openai import OpenAI
from utils import call_model

# Initialize OpenAI client for audio services (TTS and Whisper)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class StoryInterviewer:
    """
    Audio interview conductor for story personalization.
    
    Manages a voice-based Q&A session that gathers specific details
    to enhance a story. Questions are dynamically generated based on
    the story idea and spoken aloud, while answers are transcribed
    from voice recordings.
    
    Attributes:
        qa_pairs (list): List of dicts containing question-answer pairs
    """
    
    def __init__(self):
        """Initialize a new interview session with empty Q&A storage."""
        self.qa_pairs = []
    
    def generate_questions(self, sanitized_prompt: str) -> list:
        """
        Generate personalized follow-up questions using LLM.
        
        Uses model to create 2 contextual questions that will help
        personalize the story. Questions are tailored to the specific
        story idea and designed to be easy for children to answer.
        
        The LLM is prompted to ask about:
        - Character details (colors, names, traits)
        - Setting preferences (locations, time, elements)
        - Plot/emotional connections
        
        Args:
            sanitized_prompt (str): Safe, filtered story idea
            
        Returns:
            list: Exactly 2 question strings
            
        Note: Returns fallback questions if LLM parsing fails
        """
        prompt = f"""
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
        
        response = call_model(prompt, temperature=0.7, max_tokens=150)
        
        # Parse numbered questions
        questions = []
        for line in response.strip().split('\n'):
            line = line.strip()
            # Look for lines starting with numbers or bullets
            if line and (line[0].isdigit() or line.startswith('-')):
                # Remove numbering/bullets
                clean = line.lstrip('0123456789.-) ').strip()
                if clean and '?' in clean:  # Ensure it's a question
                    questions.append(clean)
        
        # Ensure we have exactly 2 questions
        if len(questions) < 2:
            # Fallback questions if parsing fails
            questions = [
                "What is your favorite color for the main character?",
                "Where would you like this story to take place?"
            ]
        
        return questions[:2]
    
    def text_to_speech(self, text: str, output_path: str) -> str:
        """
        Convert text to spoken audio using OpenAI TTS.
        
        Uses the "nova" voice (warm, friendly) at 95% speed for clarity.
        The audio file is saved to the specified path for playback in the UI.
        
        Args:
            text (str): Question text to speak
            output_path (str): Where to save the MP3 file
            
        Returns:
            str: Path to generated audio file, or None if generation failed
            
        API Used: OpenAI TTS-1 (fast, good quality)
        Cost: ~$0.015 per 1000 characters
        """
        try:
            response = client.audio.speech.create(
                model="tts-1",
                voice="nova",  # Warm, friendly female voice (good for kids)
                input=text,
                speed=0.95  # Slightly slower for clarity
            )
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Write audio to file
            response.stream_to_file(output_path)
            
            return output_path
        
        except Exception as e:
            print(f"Error generating TTS: {e}")
            return None
    
    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe voice recording to text using OpenAI Whisper.
        
        Converts the user's spoken answer into text that can be
        incorporated into the story prompt. Handles various audio
        formats (WebM from browser, WAV, MP3, etc.).
        
        Args:
            audio_file_path (str): Path to audio file to transcribe
            
        Returns:
            str: Transcribed text, or empty string if transcription failed
            
        API Used: OpenAI Whisper-1
        Cost: ~$0.006 per minute of audio
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en",
                    response_format="text"
                )
            
            return transcript.strip()
        
        except Exception as e:
            print(f"Error transcribing audio: {e}")
            return ""
    
    def add_qa_pair(self, question: str, answer: str):
        """
        Store a question-answer pair.
        """
        self.qa_pairs.append({
            'question': question,
            'answer': answer
        })
    
    def synthesize_enhanced_prompt(self, original_prompt: str) -> str:
        """
        Create an enriched story prompt from interview data.
        
        Takes the original story idea and all Q&A pairs, then uses
        an LLM to weave them into a single, detailed prompt that
        naturally incorporates all the personalized details.
        
        Example:
            Original: "A dragon learning to fly"
            Q&A: "Color?" → "Purple", "Helper?" → "Owl Oliver"
            Enhanced: "A purple dragon learning to fly with wise owl Oliver"
        
        Args:
            original_prompt (str): Initial story idea
            
        Returns:
            str: Enhanced prompt with all interview details integrated
        """
        if not self.qa_pairs:
            return original_prompt
        
        qa_text = "\n".join([
            f"- {qa['question']} → {qa['answer']}" 
            for qa in self.qa_pairs
        ])
        
        prompt = f"""
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
        
        enhanced = call_model(prompt, temperature=0.5, max_tokens=200)
        return enhanced.strip()
    
    def get_conversation_summary(self) -> list:
        """
        Return all Q&A pairs for display/logging.
        """
        return self.qa_pairs
