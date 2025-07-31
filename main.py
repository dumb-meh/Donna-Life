from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.voice_assistant.voice_assistant_route import router as voice_assistant_router
from app.services.speech_to_text.speech_to_text_route import router as speech_to_text_router
from app.services.text_to_speech.text_to_speech_route import router as text_to_speech_router
from app.services.chat.chat_route import router as chat_router

app = FastAPI(
    title="Voice Assistant API",
    description="A voice assistant that processes audio clips, creates tasks, and provides chat functionality with task context",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(voice_assistant_router, prefix="/voice-assistant", tags=["Voice Assistant"])
app.include_router(chat_router, prefix="/chat", tags=["Chat"])

@app.get("/")
async def root():
    return {"message": "Voice Assistant API is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8029)

