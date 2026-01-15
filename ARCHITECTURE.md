# 🏗️ System Architecture

## Overview

The AI Storybook Generator is a Flask-based web application that orchestrates multiple AI models to create personalized children's stories with illustrations and narration.

## Architecture Diagram

```
┌────────────────────────────────────────────────────────┐
│                   User Interface                        │
│  Templates: base, index, interview, story, anthology   │
└───────────────────────┬────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────┐
│                 Flask Application (app.py)             │
│  Routes: /, /generate, /interview/*, /story, /anthology│
└────────┬───────────────────────────────────────────────┘
         │
         ├────────────────────┬───────────────────────────┐
         ▼                    ▼                           │
┌─────────────────┐  ┌──────────────────┐               │
│   Generator     │  │   Interviewer    │               │
│ (generator.py)  │  │ (interviewer.py) │               │
│ • Sanitize      │  │ • Gen Questions  │               │
│ • Brainstorm    │  │ • TTS/Whisper   │               │
│ • Judge/Revise  │  │ • Enhance Prompt │               │
│ • Write & Refine│  └──────────────────┘               │
└────────┬────────┘                                       │
         │                                                │
         ├──────────┬──────────┬──────────┬──────────────┘
         ▼          ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
    │ Judge  │ │Revisor │ │Storybook││ Utils  │
    │(8 types│ │        │ │(images)│ │(API)   │
    └────────┘ └────────┘ └────────┘ └────────┘
         │          │          │          │
         └──────────┴──────────┴──────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │   OpenAI Services    │
         │ • GPT-3.5 • DALL-E 3 │
         │ • TTS-1  • Whisper   │
         └──────────────────────┘
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│               Data Persistence                          │
│ • SQLite (stories.db) • Files (static/stories/<uuid>/) │
└────────────────────────────────────────────────────────┘
```

## Component Breakdown

### 1. Flask Application (`app.py`)

**Responsibilities**:
- HTTP request handling
- Route definitions
- Database operations
- Template rendering
- Session management

**Key Routes**:
- `GET /`: Render story creation form
- `POST /generate`: Trigger story generation (quick mode)
- `GET /interview`: Audio interview interface
- `POST /interview/start`: Initialize voice Q&A session
- `POST /interview/answer`: Process voice answers (Whisper transcription)
- `POST /interview/generate/<session_id>`: Generate story from interview
- `GET /story/<uuid>`: Display specific story
- `GET /anthology`: List all stories
- `POST /delete/<uuid>`: Delete story

### 2. Story Generator Service (`services/generator.py`)

**Responsibilities**:
- Orchestrate multi-step story creation
- Manage execution logging
- Handle async operations
- Control feature flags (audio/images)

**Pipeline Steps**:
1. **Sanitization** - Safety filter for inappropriate content
   
2. **Brainstorming** - Generate 3 unique concept hooks
   
3. **Brainstorm Quality Loop** - Judge and revise brainstorm ideas (up to 5 iterations)
   - Safety Judge: Age-appropriate concepts
   - Concreteness Judge: Specific, not abstract
   - Uniqueness Judge: Creative, not cliché
   - Sensory Judge: Vivid imagery and details
   
4. **Planning** - Select best concept, define characters, plot, moral
   
5. **Writing** - Generate full story (700-1100 words)
   
6. **Story Quality Loop** - Judge and revise story (up to 10 iterations)
   - Safety Judge: Content appropriateness
   - Comprehensibility Judge: Logic and clarity
   - Writing Judge: Prose quality
   - Thematic Judge: Moral consistency
   
7. **Asset Generation** (Optional, controlled by flags)
   - Audio: OpenAI TTS narration
   - Images: DALL-E 3 illustrations with character consistency

### 3. Judge System (`judge.py`)

**Responsibilities**:
- Multi-faceted evaluation at two stages: brainstorm and story
- Parallel async judging
- Score aggregation

**Brainstorm Judges** (evaluate ideas before planning):
- Safety Judge: Age-appropriate concepts
- Concreteness Judge: Specific vs abstract ideas
- Uniqueness Judge: Creative vs cliché concepts
- Sensory Judge: Vivid imagery potential

**Story Judges** (evaluate completed stories):
- Safety Judge: Content appropriateness
- Comprehensibility Judge: Logic and clarity
- Writing Judge: Prose quality and style
- Thematic Judge: Moral consistency

**Scoring**:
- Each judge: 1-5 scale
- Pass threshold: Average ≥ 4.0
- All individual scores ≥ 3

### 4. Revisor System (`revisor.py`)

**Responsibilities**:
- Revise brainstorm ideas based on judge feedback
- Revise story text based on critique
- Preserve core narrative while making targeted improvements

### 5. Image Generator (`storybook.py`)

**Responsibilities**:
- Character consistency enforcement
- Parallel image generation
- Prompt engineering for DALL-E 3

**Strategy**:
1. Extract consistency guide from story
2. Generate first image (capture revised prompt)
3. Lock character details for remaining images
4. Generate remaining images in parallel

### 6. Audio Interviewer Service (`services/interviewer.py`)

**Responsibilities**:
- Generate contextual follow-up questions using LLM
- Convert questions to speech (OpenAI TTS)
- Transcribe voice answers (OpenAI Whisper)
- Synthesize enhanced prompts from Q&A pairs

**Flow**: User prompt → 2 voice questions → transcribed answers → enhanced prompt

### 7. Database Models (`models.py`)

**Tables**:

**Story**:
- `id`: Primary key
- `uuid`: Unique identifier (for folders)
- `title`: Story title
- `prompt`: Final prompt used for generation
- `original_prompt`: Pre-interview prompt (if applicable)
- `interview_data`: JSON of Q&A pairs (if applicable)
- `story_text`: Full story content
- `audio_filename`: Path to MP3 (nullable)
- `created_at`: Timestamp
- Relationship: `images` (one-to-many)

**StoryImage**:
- `id`: Primary key
- `story_id`: Foreign key to Story
- `image_filename`: Path to PNG
- `page_number`: Display order

### 8. Utilities (`utils.py`)

**Responsibilities**:
- OpenAI API wrappers
- Synchronous and async model calls
- Error handling and retries

## Data Flow

### Story Creation Flow

```
User Input
    ↓
Sanitization (GPT-4o)
    ↓
Brainstorming (GPT-4o)
    ↓
    ┌──────────────────┐
    │ Brainstorm Judge │ ← (Up to 3 iterations)
    │  ↓               │
    │ Revise Ideas     │
    └──────────────────┘
    ↓
Planning (GPT-4o)
    ↓
Writing (GPT-4o)
    ↓
    ┌──────────────────┐
    │ Story Judge Loop │ ← (Up to 10 iterations)
    │  ↓               │
    │ Revise Story     │
    └──────────────────┘
    ↓
Final Story Text
    ↓
    ├── Audio Generation (TTS-1) [Optional]
    │      ↓
    │   story.mp3
    │
    └── Image Generation (DALL-E 3) [Optional]
           ↓
        page_1.png ... page_N.png
    ↓
Save to Database
    ↓
Display to User
```

### Interview Flow (Optional Path)

```
User Input (Brief Prompt)
    ↓
Generate 2 Follow-up Questions (GPT-4o)
    ↓
Question → TTS → Audio Playback
    ↓
User Voice Answer → Whisper Transcription
    ↓
(Repeat for 2nd question)
    ↓
Synthesize Enhanced Prompt (Original + Q&A)
    ↓
Enter Normal Story Generation Pipeline
```

### Storage Organization

```
static/
└── stories/
    └── <story-uuid>/
        ├── audio/
        │   └── story.mp3
        └── images/
            ├── page_1.png
            ├── page_2.png
            └── ...
```

## Scalability Considerations

### Current Limitations
- **Single-threaded processing**: One story at a time
- **Synchronous Flask**: Blocks during generation
- **Local file storage**: Not suitable for distributed systems

### Scaling Strategies

**Short-term**:
- Add Redis/Celery for async task queue
- Separate worker processes for generation
- Implement WebSocket for real-time progress

**Long-term**:
- Migrate to cloud storage (S3/GCS)
- Use PostgreSQL instead of SQLite
- Deploy with Kubernetes for horizontal scaling
- Add CDN for static assets
- Implement caching layer

## Security Considerations

- Input sanitization at multiple levels
- API key stored in environment variables
- SQL injection prevention (SQLAlchemy ORM)
- File path validation for UUID-based folders
- Rate limiting (recommended for production)

## Performance Optimizations

1. **Parallel Judge Evaluation**: All 4 judges run simultaneously via `asyncio.gather()`
2. **Parallel Image Generation**: Multiple DALL-E requests processed concurrently
3. **Two-Stage Quality Gates**: Catch issues early (brainstorm) vs late (story)
4. **Character Locking**: Reuse first DALL-E revised prompt for consistency
5. **Feature Flags**: Toggle audio/images for faster development iteration
6. **Database Indexing**: UUID indexed for fast lookups

## Technology Stack

- **Backend**: Flask 3.0, Python 3.8+
- **Database**: SQLAlchemy + SQLite
- **AI Models**: OpenAI GPT-4o, DALL-E 3, TTS-1, Whisper
- **Frontend**: Jinja2, HTML5, CSS3, Vanilla JS (MediaRecorder API)
- **Deployment**: Gunicorn, systemd (production)

## Future Enhancements

- Async task queue (Celery + Redis) for background generation
- User authentication and multi-tenancy
- Story series with character consistency (vector embeddings + RAG)
- Story editing and regeneration
- Multiple language support
- Custom voice/style selection
- Story sharing and export (PDF/ePub)
