from fastapi import APIRouter, HTTPException
from .text_to_speech import TextToSpeechService
from .text_to_speech_schema import TextToSpeechRequest


router = APIRouter()
tts_service = TextToSpeechService()

@router.post("/greetings")
async def generate_and_save_greeting(request: TextToSpeechRequest):
    try:
        filepath = await tts_service.convert_text_to_speech_and_save(
            text=request.text,
            user_id=request.user_id,
            greeting_no=request.greeting_no
        )
        return {"message": "Audio saved", "filepath": filepath}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")
