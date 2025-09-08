from fastapi import APIRouter, HTTPException
from .greetings import Greetings
from .greetings_schema import GreetingsRequest


router = APIRouter()
tts_service = Greetings()

@router.post("/greetings")
async def generate_and_save_greetings(request: GreetingsRequest):
    try:
        filepaths = await tts_service.convert_text_to_speech_and_save(
            user_id=request.user_id,
            user_name=request.user_name
        )
        return {"message": "Audio files saved", "filepaths": filepaths}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating audio: {str(e)}")
