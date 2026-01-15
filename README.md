# AI Storybook Generator
[Diagram.pdf](https://github.com/user-attachments/files/24629861/Diagram.pdf)

An intelligent web application that creates personalized, illustrated children's stories with AI-powered narration.

##  Features

- ** Audio Interview Mode**: Interactive voice Q&A to personalize stories
- ** AI-Generated Stories**: Creates unique, age-appropriate tales (ages 5-10)
- ** Custom Illustrations**: DALL-E 3 generates consistent character artwork
- ** Audio Narration**: Text-to-speech brings stories to life
- ** Story Anthology**: Browse and revisit all your magical tales
- ** Content Safety**: Built-in filtering for appropriate content
- ** Quality Refinement**: Multi-pass AI review ensures high-quality output

##  Quick Start

### Prerequisites

- Python 3.8+
- OpenAI API key

### Installation

1. **Clone the repository**
```bash
cd "AI Agent Deployment Engineer Takehome"
```

2. **Set up environment variables**
```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

3. **Run the startup script**
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

4. **Open your browser**
```
http://localhost:8080
```

##  Usage

### Creating a Story

**Quick Mode:**
1. Navigate to the homepage
2. Enter your story prompt (e.g., "A dragon who learns to bake cookies")
3. Click "Generate Story" 
4. Wait 2-5 minutes for the magic to happen
5. Enjoy your personalized illustrated story!

**Audio Interview Mode (NEW!):**
1. Navigate to the homepage
2. Enter your basic story idea
3. Click "Audio Interview" 
4. Answer 2 voice questions to personalize your story
5. Story generates automatically with your custom details!

### Browsing the Anthology

- Click "Anthology" in the navigation
- View all your past stories
- Click "Read Story" to revisit any tale
- Delete stories you no longer want

##  Configuration

### Debug Flags

Control feature generation in `services/generator.py`:

```python
ENABLE_AUDIO = False   # Toggle audio narration
ENABLE_IMAGES = False  # Toggle image generation
```

Set these to `True` when you're ready for full story generation.

##  Project Structure

```
.
├── app.py                  # Flask application & routes
├── models.py              # Database models (Story, StoryImage)
├── services/
│   └── generator.py       # Core story generation logic
├── templates/             # Jinja2 HTML templates
│   ├── base.html
│   ├── index.html
│   ├── anthology.html
│   └── story.html
├── static/
│   └── stories/           # Generated stories with images & audio
├── judge.py               # Story quality evaluation
├── revisor.py             # Story refinement logic
├── storybook.py          # Image generation orchestration
├── utils.py              # Model calling utilities
└── requirements.txt      # Python dependencies
```

##  Development

### Running in Debug Mode

The app runs in debug mode by default on port 8080:

```python
app.run(debug=True, host='0.0.0.0', port=8080)
```

### Database

- Uses SQLite (`stories.db`)
- Auto-creates tables on first run
- Stores story metadata and file paths



