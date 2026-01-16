# System Architecture

## Overview

The AI Storybook Generator is a Flask web application that orchestrates multiple AI agents to create personalized children's stories with illustrations and audio narration. The system employs a multi-stage pipeline with quality control loops to ensure safe, creative, and well-written content.

## Core Components

### Flask Application (`app.py`)

The main web server handling HTTP requests and coordinating services.

**Key Routes:**
- `GET /` - Story creation form
- `POST /generate` - Trigger story generation
- `GET /interview` - Audio interview interface
- `POST /interview/start` - Initialize voice Q&A
- `POST /interview/answer` - Process voice responses
- `POST /interview/generate/<id>` - Generate from interview
- `GET /story/<uuid>` - View specific story
- `GET /anthology` - Browse all stories
- `POST /delete/<uuid>` - Delete story

### Story Generation Pipeline (`services/generator.py`)

Orchestrates the multi-agent story creation process:

1. **Input Sanitization** - Filters inappropriate content
2. **Brainstorming** - Generates 3 unique story concepts
3. **Brainstorm Quality Control** - Judges and revises ideas (up to 5 iterations)
4. **Story Planning** - Selects best concept, defines structure
5. **Story Writing** - Generates full narrative (700-1100 words)
6. **Story Quality Control** - Judges and revises text (up to 10 iterations)
7. **Asset Generation** - Creates audio narration and illustrations

Feature flags (`ENABLE_AUDIO`, `ENABLE_IMAGES`) control asset generation for debugging.

### Audio Interview Service (`services/interviewer.py`)

Enables voice-based story personalization:

1. Generates 2 contextual follow-up questions (GPT)
2. Converts questions to speech (OpenAI TTS)
3. Transcribes user answers (OpenAI Whisper)
4. Synthesizes enhanced prompt from Q&A (GPT)

### Judge System (`judge.py`)

Implements 8 specialized AI judges in two stages:

**Brainstorm Judges:**
- Safety: Age-appropriate concepts
- Concreteness: Specific vs abstract
- Uniqueness: Creative vs cliche
- Sensory: Vivid imagery potential

**Story Judges:**
- Safety: Content appropriateness
- Comprehensibility: Logic and clarity
- Writing: Prose quality
- Thematic: Moral consistency

Each judge scores 1-5.

### Revisor System (`revisor.py`)

Applies targeted improvements based on judge feedback:
- Patches specific issues identified by judges
- Preserves core narrative structure
- Performs smoothing pass for coherence
- Separate logic for brainstorm vs story revision

### Image Generator (`storybook.py`)

Generates consistent illustrations using DALL-E 3:

1. Analyzes story to extract character consistency guide
2. Generates first image, captures revised prompt
3. Uses locked character details for subsequent images
4. Generates remaining images in parallel

### Database Models (`models.py`)

**Story Table:**
- `uuid` - Unique identifier for file organization
- `title` - Story title
- `prompt` - Final prompt used
- `original_prompt` - Pre-interview prompt (if applicable)
- `interview_data` - JSON of Q&A pairs (if applicable)
- `story_text` - Full story content
- `audio_filename` - Path to narration file
- `created_at` - Timestamp

**StoryImage Table:**
- `story_id` - Foreign key to Story
- `image_filename` - Path to illustration
- `page_number` - Display order

### Utilities (`utils.py`)

Provides wrappers for OpenAI API calls:
- `call_model()` - Synchronous GPT requests
- `acall_model()` - Asynchronous GPT requests
- Error handling and retry logic

### Prompts (`prompts/`)

Externalized prompt templates for maintainability:
- `story_generation_prompts.py` - Sanitizer, brainstormer, planner, writer
- `judge_prompts.py` - All 8 judge templates
- `revisor_prompts.py` - Revision and smoothing prompts
- `interview_prompts.py` - Question generation and synthesis
- `image_prompts.py` - Consistency and scene prompts

## Data Flow

### Standard Generation Flow

```
User Input → Sanitizer → Brainstormer → [Judge/Revise Loop] → Planner 
→ Writer → [Judge/Revise Loop] → [Audio/Images] → Database → Display
```

### Interview-Enhanced Flow

```
User Input → Sanitizer → Interviewer (TTS/Whisper Q&A) → Prompt Synthesis 
→ Brainstormer → [Standard Pipeline]
```

## Technology Stack

- **Backend**: Flask 3.0, Python 3.8+, SQLAlchemy
- **Database**: SQLite
- **AI Models**: OpenAI GPT-3.5-turbo, DALL-E 3, TTS-1, Whisper-1
- **Frontend**: Jinja2 templates, vanilla JavaScript, CSS3
- **Deployment**: Gunicorn with systemd service

## Asset Organization

Each story creates a unique folder: `static/stories/<uuid>/`

Contains:
- `story.mp3` - Audio narration
- `image_0.png`, `image_1.png`, etc. - Illustrations

Database stores relative paths for retrieval.
