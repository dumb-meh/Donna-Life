from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from .speech_to_text import SpeechToTextService
from .speech_to_text_schema import SpeechToTextRequest, SpeechToTextResponse
import base64

router = APIRouter()
speech_service = SpeechToTextService()

@router.post("/convert", response_model=SpeechToTextResponse)
async def convert_speech_to_text(request: SpeechToTextRequest):
    """
    Convert speech audio to text
    """
    try:
        result = await speech_service.convert_audio_to_text(
            audio_data=request.audio_file,
            language=request.language
        )
        
        return SpeechToTextResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

@router.post("/convert-file")
async def convert_audio_file_to_text(
    file: UploadFile = File(...),
    language: str = "en-US"
):
    """
    Convert uploaded audio file to text
    """
    try:
        # Read file content
        audio_content = await file.read()
        
        # Convert to base64 for processing
        audio_base64 = base64.b64encode(audio_content).decode('utf-8')
        
        # Process audio
        result = await speech_service.convert_audio_to_text(
            audio_data=audio_base64,
            language=language
        )
        
        return JSONResponse(content=result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing audio file: {str(e)}")