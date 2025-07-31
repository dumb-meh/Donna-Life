import tempfile
import base64
import os
from typing import Optional
from dotenv import load_dotenv
import requests
from gtts import gTTS
import io

# Load environment variables
load_dotenv()

class TextToSpeechService:
    def __init__(self):
        # No additional configuration needed for Google TTS
        pass
        
    async def convert_text_to_speech(
        self, 
        text: str, 
        language: str = "en",
        voice: str = "default",
        speed: float = 1.0
    ) -> dict:
        """
        Convert text to speech audio using Google Text-to-Speech
        
        Args:
            text: Text to convert to speech
            language: Language code
            voice: Voice type (not used with gTTS)
            speed: Speech speed (not used with gTTS)
            
        Returns:
            Dictionary with audio data and success status
        """
        try:
            # Use Google Text-to-Speech
            tts = gTTS(text=text, lang=language, slow=False)
            
            # Create temporary file for audio output
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                temp_file_path = temp_file.name
            
            # Save audio to temporary file
            tts.save(temp_file_path)
            
            # Read generated audio file
            with open(temp_file_path, 'rb') as audio_file:
                audio_data = audio_file.read()
            
            # Clean up temporary file
            os.unlink(temp_file_path)
            
            # Convert to base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            
            return {
                "audio_file": audio_base64,
                "success": True,
                "message": "Text successfully converted to speech using Google TTS",
                "file_format": "mp3"
            }
            
        except Exception as e:
            return {
                "audio_file": "",
                "success": False,
                "message": f"Error converting text to speech: {str(e)}",
                "file_format": "mp3"
            }