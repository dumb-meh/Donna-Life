from pydantic import BaseModel
from typing import Optional

class SpeechToTextRequest(BaseModel):
    audio_file: str  # Base64 encoded audio file or file path
    language: Optional[str] = "en-US"
    
class SpeechToTextResponse(BaseModel):
    text: str
    confidence: float
    language: str
    success: bool
    message: Optional[str] = None