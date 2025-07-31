# Donna Life - Voice Task Assistant
## Overview
Donna Life is an AI-powered voice assistant that lets you manage your tasks hands-free through natural voice commands. Built with FastAPI and leveraging OpenAI's advanced language models, Donna understands your spoken instructions, creates structured tasks, answers questions about your schedule, and provides contextual assistance for task management.

## Key Features
### 🎤 Voice Command Processing 
Convert spoken commands into structured tasks

### 📅 Smart Task Creation
Automatically extract task details (title, description, due date, priority)

### 💬 Contextual Chat
Ask questions about your tasks and schedule with task-aware responses

### 🌐 Multilingual Support
Process commands in various languages while maintaining English structure

### 🧠 AI-Powered Chatbot
Can assist you with all your tasks.

## Technology Stack
Backend Framework: FastAPI

AI Services: OpenAI (GPT-3.5, Whisper)

Audio Processing: PyDub, FFmpeg

Text-to-Speech: Google TTS (gTTS)

Data Modeling: Pydantic

Deployment: Docker

## Project Structure

Donna Life/
├── app/
│   ├── services/
│   │   ├── chat/                # Chat with task context
│   │   ├── speech_to_text/      # Audio-to-text conversion
│   │   ├── text_to_speech/      # Text-to-audio conversion
│   │   └── voice_assistant/     # Core voice command processing
│   └── core/
│       └── config.py            # Application configuration
├── docker-compose.yml           # Docker composition
├── Dockerfile                   # Docker container setup
├── main.py                      # FastAPI application entry point
└── requirements.txt             # Python dependencies
Setup and Installation
Prerequisites
Python 3.9+

Docker

OpenAI API key

## Installation
Clone the repository:

bash
git clone https://github.com/your-username/donna-life.git
cd donna-life
Install dependencies:

bash
pip install -r requirements.txt
Create a .env file with your OpenAI API key:

env
OPENAI_API_KEY=your-api-key-here
Running with Docker
bash
docker-compose up --build
Running Locally
bash
uvicorn main:app --host 0.0.0.0 --port 8029


## API Endpoints
Voice Assistant
POST /voice-assistant/process: Process audio file to create task

POST /voice-assistant/process-text-only: Process text command to create task

Chat
POST /chat/text: Chat using text message with task context

POST /chat/voice: Chat using voice message with task context

GET /chat/supported-audio-formats: List supported audio formats

Speech-to-Text
POST /speech-to-text/convert: Convert speech audio to text

POST /speech-to-text/convert-file: Convert uploaded audio file to text

Text-to-Speech
POST /text-to-speech/convert: Convert text to speech audio

GET /text-to-speech/voices: List available voices

