from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from .voice_assistant import VoiceAssistantService
from .voice_assistant_schema import VoiceAssistantRequest, VoiceAssistantResponse, TaskItem, TextRequest
from ..speech_to_text.speech_to_text import SpeechToTextService

router = APIRouter()
voice_assistant_service = VoiceAssistantService()
speech_to_text_service = SpeechToTextService()

@router.post("/process", response_model=VoiceAssistantResponse)
async def process_voice_assistant_request(
    date_time: str = Form(...),
    audio_file: UploadFile = File(...)
):
    """
    Process uploaded audio file to create a task JSON
    
    This endpoint:
    1. Converts uploaded audio file to text using Whisper (auto-detects language)
    2. Processes the transcribed text using OpenAI
    3. Returns a structured task JSON
    """
    try:
        # Create request object
        request = VoiceAssistantRequest(date_time=date_time)
        
        # Validate that file is provided
        if not audio_file.filename:
            raise HTTPException(
                status_code=400, 
                detail="No audio file provided"
            )
            
        # Read audio file content
        audio_content = await audio_file.read()
        
        # Step 1: Convert audio to text using speech-to-text service
        stt_result = await speech_to_text_service.convert_uploaded_file_to_text(
            file_content=audio_content,
            filename=audio_file.filename
        )
        
        if not stt_result["success"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Speech-to-text conversion failed: {stt_result['message']}"
            )
        
        transcribed_text = stt_result["text"]
        
        # Step 2: Process transcribed text with Gemini to create task
        assistant_result = await voice_assistant_service.process_voice_and_text(
            transcribed_text=transcribed_text,
            date_time=request.date_time
        )
        
        # Step 3: Create response
        if assistant_result["success"] and assistant_result["task"] is not None:
            # Successful task creation
            response = VoiceAssistantResponse(
                task=TaskItem(**assistant_result["task"]),
                success=assistant_result["success"],
                message=assistant_result["message"]
            )
        else:
            # Task creation failed, return response without task
            response = VoiceAssistantResponse(
                task=None,
                success=assistant_result["success"],
                message=assistant_result["message"]
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing voice assistant request: {str(e)}")

@router.post("/process-text-only", response_model=VoiceAssistantResponse)
async def process_text_only(request: TextRequest):
    """
    Process text only to create a task JSON (no audio)
    
    Expects a JSON body with a 'text' field, e.g.:
    {
        "text": "Call John about the project tomorrow at 2pm"
    }
    """
    try:
        # Process text with Gemini to create task
        assistant_result = await voice_assistant_service.process_voice_and_text(
            transcribed_text=request.text
        )
        
        # Create response based on success
        if assistant_result["success"] and assistant_result["task"] is not None:
            # Successful task creation
            response = VoiceAssistantResponse(
                task=TaskItem(**assistant_result["task"]),
                success=assistant_result["success"],
                message=assistant_result["message"]
            )
        else:
            # Task creation failed, return response without task
            response = VoiceAssistantResponse(
                task=None,
                success=assistant_result["success"],
                message=assistant_result["message"]
            )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing text: {str(e)}")

@router.get("/health")
async def voice_assistant_health():
    """
    Health check for voice assistant service
    """
    return {"status": "healthy", "service": "voice_assistant"}