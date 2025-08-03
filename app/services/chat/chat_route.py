from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from .chat import ChatService
from .chat_schema import ChatTextRequest, ChatVoiceRequest, ChatResponse
from ..speech_to_text.speech_to_text import SpeechToTextService
from typing import Optional, Union, Dict, Any, List
import json
import logging

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter()
chat_service = ChatService()
speech_to_text_service = SpeechToTextService()

@router.post("/text", response_model=ChatResponse)
async def chat_with_text(request: ChatTextRequest):
    """
    Chat using text message with optional task context
    """
    try:
        # Process chat message with task context
        result = await chat_service.process_chat_message(
            message=request.message,
            date_time=request.date_time,
            task_context=request.task_context
        )
        
        return ChatResponse(**result)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat message: {str(e)}")

@router.post("/voice", response_model=ChatResponse)
async def chat_with_voice(
    audio_file: UploadFile = File(...),
    task_context: Optional[str] = Form(None),
    date_time: str = Form(...)
):
    """
    Chat using voice message with optional task context
    
    This endpoint:
    1. Validates and converts uploaded audio file to optimal format (MP3/WAV)
    2. Converts processed audio file to text using Whisper
    3. Processes the transcribed text as a chat message with task context
    4. Returns AI response
    
    Supports various audio formats: MP3, WAV, FLAC, AAC, OGG, M4A, WMA, MP4, AVI, MOV, MKV, WebM, 3GP, AMR
    """
    try:
        # Validate that file is provided
        if not audio_file.filename:
            raise HTTPException(
                status_code=400, 
                detail="No audio file provided"
            )
        
        # Check if audio format is supported
        if not chat_service.is_audio_format_supported(audio_file.filename):
            supported_formats = ", ".join(chat_service.get_supported_audio_formats())
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported audio format. Supported formats: {supported_formats}"
            )
        
        # Read audio file content
        audio_content = await audio_file.read()
        
        # Step 1: Validate and convert audio format if needed
        try:
            processed_audio_content, conversion_message = chat_service._validate_and_convert_audio(
                file_content=audio_content,
                filename=audio_file.filename
            )
            
            # Log the audio processing result
            logger.info(f"Audio processing: {conversion_message}")
            
        except Exception as e:
            logger.error(f"Audio processing failed: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Audio processing failed: {str(e)}"
            )
        
        # Step 2: Convert processed audio to text using speech-to-text service
        stt_result = await speech_to_text_service.convert_uploaded_file_to_text(
            file_content=processed_audio_content,
            filename=audio_file.filename
        )
        
        if not stt_result["success"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Speech-to-text conversion failed: {stt_result['message']}"
            )
        
        transcribed_text = stt_result["text"]
        
        # Step 3: Parse task context if provided
        parsed_task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
        if task_context:
            try:
                parsed_task_context = json.loads(task_context)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON format in task_context"
                )
        
        # Step 4: Process chat message with task context
        result = await chat_service.process_chat_message(
            message=transcribed_text,
            date_time=date_time,
            task_context=parsed_task_context
        )
        
        return ChatResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing voice chat: {str(e)}")

@router.get("/supported-audio-formats")
async def get_supported_audio_formats():
    """
    Get list of supported audio formats for voice chat
    """
    return {
        "supported_formats": chat_service.get_supported_audio_formats(),
        "preferred_format": chat_service.preferred_output_format,
        "description": "Upload audio files in any of these formats. They will be automatically converted to the optimal format for processing."
    }

@router.get("/health")
async def chat_health():
    """
    Health check for chat service
    """
    # Check if FFmpeg is available for audio processing
    ffmpeg_available = chat_service._ensure_ffmpeg_available()
    supported_formats = chat_service.get_supported_audio_formats()
    
    return {
        "status": "healthy", 
        "service": "chat",
        "audio_processing": {
            "ffmpeg_available": ffmpeg_available,
            "supported_formats": supported_formats,
            "preferred_output_format": chat_service.preferred_output_format
        }
    }
