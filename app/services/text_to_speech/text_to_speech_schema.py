from pydantic import BaseModel
from typing import Optional

class TextToSpeechRequest(BaseModel):
    text: str
    language: Optional[str] = "en"
    voice: Optional[str] = "default"
    speed: Optional[float] = 1.0
    
class TextToSpeechResponse(BaseModel):
    audio_file: str  # Base64 encoded audio file
    success: bool
    message: Optional[str] = None
    file_format: str = "wav"