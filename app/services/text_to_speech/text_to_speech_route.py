from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from .text_to_speech import TextToSpeechService
from .text_to_speech_schema import TextToSpeechRequest, TextToSpeechResponse

router = APIRouter()
tts_service = TextToSpeechService()

@router.post("/convert", response_model=TextToSpeechResponse)
async def convert_text_to_speech(request: TextToSpeechRequest):
    """
    Convert text to speech audio
    """
    try:
        result = await tts_service.convert_text_to_speech(
            text=request.text,
            language=request.language,
            voice=request.voice,
            speed=request.speed
        )
        
        return TextToSpeechResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting text to speech: {str(e)}")

@router.get("/voices")
async def get_available_voices():
    """
    Get list of available voices for Google TTS
    """
    try:
        # Google TTS supported languages
        languages = [
            {"id": "en", "name": "English", "language": ["en"]},
            {"id": "es", "name": "Spanish", "language": ["es"]},
            {"id": "fr", "name": "French", "language": ["fr"]},
            {"id": "de", "name": "German", "language": ["de"]},
            {"id": "it", "name": "Italian", "language": ["it"]},
            {"id": "pt", "name": "Portuguese", "language": ["pt"]},
            {"id": "ru", "name": "Russian", "language": ["ru"]},
            {"id": "ja", "name": "Japanese", "language": ["ja"]},
            {"id": "ko", "name": "Korean", "language": ["ko"]},
            {"id": "zh", "name": "Chinese", "language": ["zh"]},
        ]
        
        return JSONResponse(content={"voices": languages})
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting voices: {str(e)}")