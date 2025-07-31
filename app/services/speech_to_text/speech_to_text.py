import openai
import io
import base64
from pydantic import BaseModel
from typing import Optional
import tempfile
import os
from dotenv import load_dotenv
from pydub import AudioSegment

# Load environment variables
load_dotenv()

class SpeechToTextService:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    def _convert_to_supported_format(self, input_path: str, output_path: str) -> bool:
        """
        Convert audio file to WAV format (supported by Whisper) using pydub
        
        Args:
            input_path: Path to input audio file
            output_path: Path to output WAV file
            
        Returns:
            True if conversion successful, False otherwise
        """
        try:
            # Load audio file with pydub (supports many formats)
            audio = AudioSegment.from_file(input_path)
            
            # Export as WAV (16-bit PCM, which is widely supported)
            audio.export(output_path, format="wav")
            return True
            
        except Exception as e:
            print(f"Error converting audio to WAV: {str(e)}")
            return False
    
    async def convert_audio_to_text(self, audio_data: str, language: str = None) -> dict:
        """
        Convert audio to text using OpenAI Whisper
        
        Args:
            audio_data: Base64 encoded audio data or file path
            language: Language code for recognition (if None, auto-detect)
            
        Returns:
            Dictionary with text, confidence, and success status
        """
        try:
            # Check if audio_data is base64 or file path
            if audio_data.startswith('data:audio'):
                # Handle base64 audio data
                audio_bytes = base64.b64decode(audio_data.split(',')[1])
            elif os.path.exists(audio_data):
                # Handle file path
                with open(audio_data, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
            else:
                # Assume it's raw base64
                audio_bytes = base64.b64decode(audio_data)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_file.write(audio_bytes)
                temp_file_path = temp_file.name
            
            try:
                # Use OpenAI Whisper with auto-detection if no language specified
                with open(temp_file_path, 'rb') as audio_file:
                    if language:
                        # Use specified language
                        transcript = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language=language.split('-')[0] if '-' in language else language
                        )
                    else:
                        # Auto-detect language
                        transcript = self.client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                
                return {
                    "text": transcript.text,
                    "confidence": 0.95,  # Whisper doesn't provide confidence, using default
                    "language": language or "auto-detected",
                    "success": True,
                    "message": "Speech successfully converted to text using Whisper"
                }
                
            finally:
                # Clean up temporary file
                os.unlink(temp_file_path)
                
        except openai.OpenAIError as e:
            return {
                "text": "",
                "confidence": 0.0,
                "language": language or "unknown",
                "success": False,
                "message": f"OpenAI API error: {str(e)}"
            }
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "language": language or "unknown",
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }
    
    async def convert_uploaded_file_to_text(self, file_content: bytes, filename: str) -> dict:
        """
        Convert uploaded audio file to text using OpenAI Whisper
        Always converts to WAV format before processing (Whisper supported format)
        
        Args:
            file_content: Raw audio file bytes
            filename: Original filename (used for extension detection)
            
        Returns:
            Dictionary with text, confidence, and success status
        """
        try:
            # Determine file extension
            file_ext = os.path.splitext(filename)[1].lower()
            if not file_ext:
                file_ext = '.wav'  # Default extension
            
            # Create temporary file for original audio
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_original:
                temp_original.write(file_content)
                temp_original_path = temp_original.name
            
            # Create temporary file for WAV conversion
            temp_wav_path = temp_original_path.replace(file_ext, '.wav')
            
            try:
                # Check if file is already in a supported format
                supported_formats = ['.flac', '.m4a', '.mp3', '.mp4', '.mpeg', '.mpga', '.oga', '.ogg', '.wav', '.webm']
                
                if file_ext in supported_formats:
                    # File is already in supported format, use as is
                    processing_file = temp_original_path
                    conversion_note = f"File already in supported format ({file_ext})"
                else:
                    # Convert to WAV format
                    conversion_successful = self._convert_to_supported_format(temp_original_path, temp_wav_path)
                    
                    if conversion_successful:
                        processing_file = temp_wav_path
                        conversion_note = f"Converted from {file_ext} to WAV format"
                    else:
                        # If conversion fails, try using original file anyway
                        processing_file = temp_original_path
                        conversion_note = f"Conversion failed, using original {file_ext} format"
                
                # Use OpenAI Whisper with auto-detection
                with open(processing_file, 'rb') as audio_file:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file
                    )
                
                return {
                    "text": transcript.text,
                    "confidence": 0.95,  # Whisper doesn't provide confidence, using default
                    "language": "auto-detected",
                    "success": True,
                    "message": f"Speech successfully converted to text using Whisper ({conversion_note})"
                }
                
            finally:
                # Clean up temporary files
                if os.path.exists(temp_original_path):
                    os.unlink(temp_original_path)
                if os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
                
        except openai.OpenAIError as e:
            return {
                "text": "",
                "confidence": 0.0,
                "language": "unknown",
                "success": False,
                "message": f"OpenAI API error: {str(e)}"
            }
        except Exception as e:
            return {
                "text": "",
                "confidence": 0.0,
                "language": "unknown",
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }