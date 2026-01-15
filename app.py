"""
AI Storybook Generator - Main Flask Application

This is the main entry point for the AI Storybook Generator web application.
It provides routes for:
- Story generation (quick mode and audio interview mode)
- Story viewing and management (anthology, individual stories)
- Audio interview session management

The application uses:
- Flask for web framework
- SQLAlchemy for database management
- OpenAI GPT-3.5 turbo for story generation
- OpenAI DALL-E 3 for image generation
- OpenAI TTS for audio narration
- OpenAI Whisper for voice transcription

Author: Robert Moore
Date: January 2026
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
import sys
import re
import json
import uuid as uuid_lib

# Add the current directory to the Python path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.generator import StoryGenerator
from services.interviewer import StoryInterviewer
from models import db, Story, StoryImage

def clean_paragraph_text(text):
    """
    Clean paragraph text to remove problematic whitespace and characters.
    
    This function addresses an issue where invisible Unicode characters (like zero-width
    spaces) can cause rendering problems, particularly with the CSS drop-cap styling
    on the first letter of paragraphs.
    
    Args:
        text (str): The paragraph text to clean
        
    Returns:
        str: Cleaned text with normalized whitespace
    """
    # Remove invisible Unicode characters (e.g., zero-width spaces, non-breaking spaces)
    text = ''.join(char for char in text if char.isprintable() or char in '\n\r\t ')
    
    # Normalize all whitespace (tabs, multiple spaces, newlines) to single spaces
    text = ' '.join(text.split())
    
    return text.strip()

# ==============================================================================
# Flask Application Configuration
# ==============================================================================

app = Flask(__name__)

# Secret key for session management (should be set via environment variable in production)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - using SQLite for simplicity
# In production, consider PostgreSQL or MySQL for better performance
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stories.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database with Flask app
db.init_app(app)

# Create database tables on startup if they don't exist
with app.app_context():
    db.create_all()

# Ensure required static directories exist for storing generated content
os.makedirs('static/stories', exist_ok=True)      # Story images and audio
os.makedirs('static/interviews', exist_ok=True)  # Interview session audio

# In-memory storage for active interview sessions
# Note: This will be lost on server restart. For production, consider Redis or database storage.
interview_sessions = {}


# ==============================================================================
# Main Application Routes
# ==============================================================================

@app.route('/')
def index():
    """
    Homepage - Story creation interface.
    
    Displays the main story creation form with two options:
    1. Quick generation - immediate story creation
    2. Audio interview - interactive voice Q&A for personalization
    
    Returns:
        Rendered HTML template for the homepage
    """
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    """
    Quick story generation endpoint (no interview).
    
    Process:
    1. Validate user input
    2. Generate story through full AI pipeline (sanitize, brainstorm, plan, write, refine)
    3. Save story and associated media to database
    4. Redirect to story view page
    
    Form Data:
        prompt (str): User's story idea
        
    Returns:
        Redirect to story view page on success, or homepage with error message
        
    Note: This can take 2-5 minutes depending on enabled features (audio/images)
    """
    user_prompt = request.form.get('prompt', '').strip()
    
    if not user_prompt:
        return render_template('index.html', error="Please enter a story prompt!")
    
    # Initialize the story generator (it will create a unique UUID)
    generator = StoryGenerator()
    
    # Generate the story (this may take several minutes)
    result = generator.generate(user_prompt)
    
    if not result['success']:
        return render_template('index.html', error=f"Error generating story: {result.get('error', 'Unknown error')}")
    
    # Save story to database
    story = Story(
        uuid=result['story_uuid'],
        title=result['title'],
        prompt=user_prompt,
        story_text=result['story_text'],
        audio_filename=result['audio_path'].replace('static/', '') if result['audio_path'] else None
    )
    
    db.session.add(story)
    db.session.flush()  # Get the story.id before adding images
    
    # Save images to database
    for idx, img_path in enumerate(result['image_paths']):
        if img_path:
            story_image = StoryImage(
                story_id=story.id,
                image_filename=img_path.replace('static/', ''),
                page_number=idx
            )
            db.session.add(story_image)
    
    db.session.commit()
    
    # Redirect to the story view page
    return redirect(url_for('view_story', story_uuid=story.uuid))

@app.route('/story/<story_uuid>')
def view_story(story_uuid):
    """
    Individual story view page.
    
    Displays a complete story with:
    - Title and metadata (creation date)
    - Audio narration player (if available)
    - Story text with formatted paragraphs and drop-cap styling
    - Illustrations interspersed with text
    
    Args:
        story_uuid (str): Unique identifier for the story
        
    Returns:
        Rendered story page template, or 404 if story not found
    """
    story = Story.query.filter_by(uuid=story_uuid).first_or_404()
    
    # Split story body into paragraphs
    match = re.match(r"Title:\s*(.+?)\n\s*\n(.*)", story.story_text, re.DOTALL)
    if match:
        story_body = match.group(2)
    else:
        lines = story.story_text.split('\n')
        story_body = "\n".join(lines[1:]) if len(lines) > 1 else story.story_text
    
    # Clean paragraphs: strip whitespace and normalize spaces
    paragraphs = []
    for p in story_body.split('\n'):
        cleaned = clean_paragraph_text(p)
        if cleaned:
            paragraphs.append(cleaned)
    
    return render_template(
        'story.html',
        story=story,
        paragraphs=paragraphs
    )

@app.route('/anthology')
def anthology():
    """
    Story anthology/library page.
    
    Displays all previously generated stories in a grid layout,
    sorted by creation date (newest first). Each story shows:
    - Thumbnail image
    - Title
    - Creation date
    - Read and delete buttons
    
    Returns:
        Rendered anthology template with list of stories
    """
    stories = Story.query.order_by(Story.created_at.desc()).all()
    return render_template('anthology.html', stories=stories)

@app.route('/delete/<story_uuid>', methods=['POST'])
def delete_story(story_uuid):
    """
    Delete a story and all associated files.
    
    Removes:
    - Story record from database
    - All associated image records
    - Physical files (images and audio) from filesystem
    
    Args:
        story_uuid (str): UUID of story to delete
        
    Returns:
        Redirect to anthology page
    """
    story = Story.query.filter_by(uuid=story_uuid).first_or_404()
    
    # Delete files from filesystem
    import shutil
    story_folder = f'static/stories/{story.uuid}'
    if os.path.exists(story_folder):
        shutil.rmtree(story_folder)
    
    # Delete from database (cascade will delete images too)
    db.session.delete(story)
    db.session.commit()
    
    return redirect(url_for('anthology'))


# ==============================================================================
# Audio Interview Feature Routes
# ==============================================================================
# These routes handle the interactive voice Q&A feature that personalizes stories
# using OpenAI TTS (text-to-speech) and Whisper (speech-to-text)

@app.route('/interview', methods=['GET'])
def interview_page():
    """
    Audio interview interface page.
    
    Displays the interview UI where users answer voice questions
    to personalize their story. Requires an initial story prompt
    passed as a query parameter.
    
    Query Parameters:
        prompt (str): Initial story idea from user
        
    Returns:
        Rendered interview template, or redirect to homepage if no prompt
    """
    prompt = request.args.get('prompt', '').strip()
    
    if not prompt:
        return redirect(url_for('index'))
    
    return render_template('interview.html', prompt=prompt)

@app.route('/interview/start', methods=['POST'])
def start_interview():
    """
    Initialize a new audio interview session.
    
    Process:
    1. Sanitize user input (content safety filtering)
    2. Generate 2 contextual follow-up questions using LLM
    3. Convert first question to speech using OpenAI TTS
    4. Create session and return first question audio URL
    
    Form Data:
        prompt (str): User's initial story idea
        
    Returns:
        JSON response containing:
        - session_id: Unique identifier for this interview
        - question_audio: URL to audio file of first question
        - question_text: Text version of the question
        - question_number: Current question number (1)
        - total_questions: Total questions in interview (2)
        
    Status Codes:
        200: Success
        400: Missing or invalid prompt
    """
    user_prompt = request.form.get('prompt', '').strip()
    
    if not user_prompt:
        return jsonify({'error': 'Please enter a story prompt'}), 400
    
    # Sanitize input first (using the same logic from generator)
    generator = StoryGenerator()
    sanitized_prompt = generator.sanitize_input(user_prompt)
    
    # Create interviewer and generate questions based on sanitized input
    interviewer = StoryInterviewer()
    questions = interviewer.generate_questions(sanitized_prompt)
    
    # Create session
    session_id = str(uuid_lib.uuid4())
    
    # Generate audio for first question
    audio_path = f"static/interviews/{session_id}_q1.mp3"
    interviewer.text_to_speech(questions[0], audio_path)
    
    # Store session
    interview_sessions[session_id] = {
        'interviewer': interviewer,
        'original_prompt': user_prompt,
        'sanitized_prompt': sanitized_prompt,
        'questions': questions,
        'current_question_idx': 0
    }
    
    return jsonify({
        'session_id': session_id,
        'question_audio': url_for('static', filename=f'interviews/{session_id}_q1.mp3'),
        'question_text': questions[0],
        'question_number': 1,
        'total_questions': len(questions)
    })

@app.route('/interview/answer', methods=['POST'])
def submit_answer():
    """
    Process a voice answer to an interview question.
    
    Process:
    1. Receive audio recording from user
    2. Transcribe audio using OpenAI Whisper
    3. Store question-answer pair
    4. Either return next question or mark interview complete
    
    Form Data:
        session_id (str): Interview session identifier
        audio (file): WebM audio file of user's answer
        
    Returns:
        JSON response with either:
        - Next question data (if more questions remain)
        - Completion data with enhanced prompt (if interview finished)
        
    Status Codes:
        200: Success
        400: Missing session_id, invalid session, or transcription failed
    """
    session_id = request.form.get('session_id')
    audio_file = request.files.get('audio')
    
    if not session_id or session_id not in interview_sessions:
        return jsonify({'error': 'Invalid or expired session'}), 400
    
    if not audio_file:
        return jsonify({'error': 'No audio file provided'}), 400
    
    session_data = interview_sessions[session_id]
    interviewer = session_data['interviewer']
    current_idx = session_data['current_question_idx']
    current_question = session_data['questions'][current_idx]
    
    # Save audio file temporarily
    audio_path = f"static/interviews/{session_id}_answer_{current_idx}.webm"
    audio_file.save(audio_path)
    
    # Transcribe using Whisper
    transcription = interviewer.transcribe_audio(audio_path)
    
    if not transcription:
        return jsonify({'error': 'Could not transcribe audio. Please try again.'}), 400
    
    # Store Q&A pair
    interviewer.add_qa_pair(current_question, transcription)
    
    # Move to next question
    session_data['current_question_idx'] += 1
    
    # Check if interview is complete
    if session_data['current_question_idx'] >= len(session_data['questions']):
        # Interview complete - synthesize enhanced prompt
        enhanced_prompt = interviewer.synthesize_enhanced_prompt(
            session_data['sanitized_prompt']
        )
        
        # Store for generation route
        session_data['enhanced_prompt'] = enhanced_prompt
        session_data['completed'] = True
        
        return jsonify({
            'complete': True,
            'transcription': transcription,
            'enhanced_prompt': enhanced_prompt,
            'conversation': interviewer.get_conversation_summary()
        })
    
    # Get next question
    next_idx = session_data['current_question_idx']
    next_question = session_data['questions'][next_idx]
    
    # Generate audio for next question
    audio_path = f"static/interviews/{session_id}_q{next_idx + 1}.mp3"
    interviewer.text_to_speech(next_question, audio_path)
    
    return jsonify({
        'complete': False,
        'transcription': transcription,
        'question_audio': url_for('static', filename=f'interviews/{session_id}_q{next_idx + 1}.mp3'),
        'question_text': next_question,
        'question_number': next_idx + 1,
        'total_questions': len(session_data['questions'])
    })

@app.route('/interview/generate/<session_id>', methods=['POST'])
def generate_from_interview(session_id):
    """
    Generate personalized story from completed interview.
    
    Takes the Q&A from the interview session, synthesizes an enhanced
    story prompt, and runs the full story generation pipeline.
    
    Process:
    1. Validate interview session is complete
    2. Generate story using enhanced prompt
    3. Save story with interview data to database
    4. Clean up session
    5. Redirect to story view
    
    Args:
        session_id (str): Interview session identifier (URL parameter)
        
    Returns:
        JSON response containing:
        - success: Boolean status
        - story_uuid: Generated story identifier
        - redirect_url: URL to view the completed story
        
    Status Codes:
        200: Success
        400: Invalid or incomplete session
        500: Story generation failed
    """
    if session_id not in interview_sessions:
        return jsonify({'error': 'Invalid or expired session'}), 400
    
    session_data = interview_sessions[session_id]
    
    if not session_data.get('completed'):
        return jsonify({'error': 'Interview not completed'}), 400
    
    enhanced_prompt = session_data.get('enhanced_prompt')
    interviewer = session_data['interviewer']
    
    # Generate the story with enhanced prompt
    generator = StoryGenerator()
    result = generator.generate(enhanced_prompt)
    
    if not result['success']:
        return jsonify({'error': f"Error generating story: {result.get('error', 'Unknown error')}"}), 500
    
    # Save story to database with interview data
    story = Story(
        uuid=result['story_uuid'],
        title=result['title'],
        prompt=enhanced_prompt,
        original_prompt=session_data['original_prompt'],
        interview_data=json.dumps(interviewer.get_conversation_summary()),
        story_text=result['story_text'],
        audio_filename=result['audio_path'].replace('static/', '') if result['audio_path'] else None
    )
    
    db.session.add(story)
    db.session.flush()
    
    # Save images
    for idx, img_path in enumerate(result['image_paths']):
        if img_path:
            story_image = StoryImage(
                story_id=story.id,
                image_filename=img_path.replace('static/', ''),
                page_number=idx
            )
            db.session.add(story_image)
    
    db.session.commit()
    
    # Clean up session
    del interview_sessions[session_id]
    
    return jsonify({
        'success': True,
        'story_uuid': story.uuid,
        'redirect_url': url_for('view_story', story_uuid=story.uuid)
    })

@app.route('/health')
def health():
    """
    Health check endpoint for monitoring.
    
    Returns a simple JSON response indicating the application is running.
    Useful for container orchestration systems like Kubernetes.
    
    Returns:
        JSON with status 'healthy'
    """
    return {'status': 'healthy'}


# ==============================================================================
# Application Entry Point
# ==============================================================================

if __name__ == '__main__':
    # Run the Flask development server
    # Configuration:
    # - debug=True: Enable auto-reload and detailed error pages (disable in production)
    # - host='0.0.0.0': Allow external connections (not just localhost)
    # - port=8080: Listen on port 8080 (change if needed)
    #
    # For production deployment, use a WSGI server like Gunicorn instead:
    # gunicorn -c gunicorn.conf.py app:app
    app.run(debug=True, host='0.0.0.0', port=8080)
