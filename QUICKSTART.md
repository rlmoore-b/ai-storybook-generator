# Quick Start Guide

Get your AI Storybook Generator running in 3 minutes!

## Prerequisites

- Python 3.8 or higher
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

## Step 1: Setup Environment

Create a `.env` file in the project root:

```bash
echo "OPENAI_API_KEY=sk-your-key-here" > .env
```

Replace `sk-your-key-here` with your actual OpenAI API key.

## Step 2: Run the Server

### Option A: Use the Start Script (Recommended)

```bash
chmod +x start_server.sh
./start_server.sh
```

### Option B: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python3 app.py
```

## Step 3: Open Your Browser

Navigate to:
```
http://localhost:8080
```

 **You're ready to create stories!**

## First Story

1. Click "New Story" (if not already there)
2. Enter a prompt like:
   - "A curious robot discovers emotions"
   - "A dragon who is afraid of flying"
   - "Friends on an underwater adventure"
3. Click "Generate My Story" ✨
4. Wait 2-5 minutes (grab a coffee ☕)
5. Enjoy your personalized story!

## Important Notes

 **Debug Mode**: By default, audio and images are **disabled** for faster testing.

To enable them, edit `services/generator.py`:

```python
ENABLE_AUDIO = True   # Enable audio narration
ENABLE_IMAGES = True  # Enable AI-generated images
```

## Troubleshooting

### "Module not found: flask"
```bash
python3 -m pip install flask
```

### "Port 8080 already in use"
```bash
# Kill the process on port 8080
lsof -ti:8080 | xargs kill -9

# Or change the port in app.py
app.run(debug=True, host='0.0.0.0', port=5001)
```

### "OpenAI API Error"
- Check your `.env` file has the correct API key
- Verify your OpenAI account has credits
- Test your key at: https://platform.openai.com/account/usage

## Next Steps

- Read the full [README.md](README.md) for detailed features
- Check [DEBUG_FLAGS.md](DEBUG_FLAGS.md) to enable audio/images
- Explore the [Anthology](http://localhost:8080/anthology) to view past stories

Happy story creation! 📖✨
