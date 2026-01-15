#!/bin/bash

# AI Storybook Flask Server Startup Script

echo "Starting AI Storybook Generator..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found!"
    echo "Please create a .env file with your OPENAI_API_KEY"
    echo "Example: OPENAI_API_KEY=sk-your-key-here"
    exit 1
fi

# Run the Flask app
echo "Starting Flask server on http://localhost:8080"
echo "Press Ctrl+C to stop the server"
python3 app.py
