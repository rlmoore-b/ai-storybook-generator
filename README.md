# AI Storybook Generator

A Flask web application that creates personalized, illustrated children's stories using AI agents with multi-stage quality control.

## System Architecture

[View Architecture Diagram (PDF)](https://github.com/user-attachments/files/24681282/Storybook_Generator_Diagram_Robert_Moore.pdf)

## Features

- **AI-Generated Stories**: Creates unique, age-appropriate tales (ages 5-10)
- **Audio Interview Mode**: Interactive voice Q&A to personalize stories
- **Custom Illustrations**: DALL-E 3 generates consistent character artwork
- **Audio Narration**: Text-to-speech brings stories to life
- **Story Anthology**: Browse and revisit all your generated tales
- **Content Safety**: Built-in filtering for appropriate content
- **Quality Refinement**: Multi-agent review ensures high-quality output

## Quick Start

### Prerequisites

- Python 3.8 or higher
- OpenAI API key with credits

### Installation

1. Set up environment variables:
```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

2. Run the startup script:
```bash
./start_server.sh
```

Or manually:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

3. Open your browser to `http://localhost:8080`

## Usage

### Creating a Story

**Quick Mode:**
1. Navigate to homepage
2. Enter story prompt (e.g., "A dragon who learns to bake cookies")
3. Click "Generate Story"
4. Wait 2-5 minutes for generation
5. Enjoy your personalized illustrated story

**Audio Interview Mode:**
1. Navigate to homepage
2. Enter basic story idea
3. Click "Audio Interview"
4. Answer 2 voice questions to personalize
5. Story generates automatically with custom details

### Managing Stories

- Click "Anthology" to view all stories
- Click "Read Story" to revisit any tale
- Delete stories you no longer want

## Configuration

### Debug Flags

Control feature generation in `services/generator.py`:

```python
ENABLE_AUDIO = True    # Toggle audio narration
ENABLE_IMAGES = True   # Toggle image generation
```

Set to `False` for faster debugging without asset generation.

## Project Structure

```
.
├── app.py                      # Flask routes and application logic
├── models.py                   # Database models (SQLAlchemy)
├── services/
│   ├── generator.py            # Story generation pipeline
│   └── interviewer.py          # Audio interview service
├── prompts/
│   ├── story_generation_prompts.py
│   ├── judge_prompts.py
│   ├── revisor_prompts.py
│   ├── interview_prompts.py
│   └── image_prompts.py
├── judge.py                    # Story quality evaluation (8 judges)
├── revisor.py                  # Story refinement logic
├── storybook.py                # Image generation with consistency
├── utils.py                    # OpenAI API wrappers
├── templates/                  # Jinja2 HTML templates
├── static/stories/             # Generated content (per UUID)
└── requirements.txt
```

## How It Works

The application uses a multi-stage AI pipeline:

1. **Sanitization**: Filters inappropriate input
2. **Brainstorming**: Generates 3 unique story concepts
3. **Brainstorm Quality Loop**: 4 judges evaluate and revise ideas
4. **Planning**: Selects best concept, defines structure
5. **Writing**: Generates full story
6. **Story Quality Loop**: 4 judges evaluate and revise text
7. **Asset Generation**: Creates illustrations and audio narration

See `ARCHITECTURE.md` for detailed technical documentation.

## Development

### Database

- SQLite database (`stories.db`)
- Auto-creates on first run
- Stores story metadata and file paths

### Running Tests

The application runs in debug mode by default. For production deployment:

```bash
gunicorn -c gunicorn.conf.py app:app
```

## Troubleshooting

### Port Already in Use

```bash
lsof -ti:8080 | xargs kill -9
```

### Module Not Found

Ensure you're using the correct Python environment:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

### OpenAI API Errors

- Verify API key in `.env` file
- Check account has available credits
- Ensure stable internet connection

## Technical Notes

- Story generation takes 2-5 minutes depending on features enabled
- Each story creates a unique folder: `static/stories/<uuid>/`
- Character consistency maintained across illustrations using locked prompts
- All AI calls use OpenAI models (GPT-3.5-turbo, DALL-E 3, TTS-1, Whisper-1)

## Code Organization

- `main.py` contains the answer to the "If I had two more hours" question
- All production code is in the Flask application
- Prompts are externalized in `prompts/` for maintainability
- Services follow separation of concerns principle

