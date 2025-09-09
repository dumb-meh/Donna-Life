import openai
import json
from typing import Optional, Dict, Any, List, Union
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import re
import logging
import tempfile
from pydub import AudioSegment
from pydub.utils import which
from app.services.voice_assistant.voice_assistant import VoiceAssistantService
                
                

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
voice_assistant =  VoiceAssistantService()

class ChatService:
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        self.supported_input_formats = [
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', 
            '.mp4', '.avi', '.mov', '.mkv', '.webm', '.3gp', '.amr'
        ]
        self.preferred_output_format = 'mp3'  
    
    def _ensure_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available for audio processing"""
        try:
            return which("ffmpeg") is not None
        except Exception:
            return False
    
    def _convert_audio_format(self, input_file_path: str, output_format: str = 'mp3') -> Optional[str]:
        """
        Convert audio file to specified format using pydub
        """
        try:
            audio = AudioSegment.from_file(input_file_path)
            if audio.channels > 1:
                audio = audio.set_channels(1)
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
            base_name = os.path.splitext(input_file_path)[0]
            output_file_path = f"{base_name}_converted.{output_format}"
            if output_format == 'mp3':
                audio.export(output_file_path, format="mp3", bitrate="64k")
            elif output_format == 'wav':
                audio.export(output_file_path, format="wav")
            else:
                audio.export(output_file_path, format=output_format)
            logger.info(f"Successfully converted audio to {output_format} format")
            return output_file_path
        except Exception as e:
            logger.error(f"Error converting audio format: {str(e)}")
            return None
    
    def _validate_and_convert_audio(self, file_content: bytes, filename: str) -> tuple[bytes, str]:
        """
        Validate and convert audio file to optimal format for processing
        
        Args:
            file_content: Raw audio file bytes
            filename: Original filename
            
        Returns:
            Tuple of (converted_file_content, conversion_message)
        """
        try:
            file_ext = os.path.splitext(filename)[1].lower()
            
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            conversion_message = f"Original format: {file_ext}"
            
            try:
                if file_ext not in ['.mp3', '.wav', '.flac', '.m4a', '.ogg']:
                    logger.info(f"Converting unsupported format {file_ext} to {self.preferred_output_format}")
                    
                    converted_path = self._convert_audio_format(temp_file_path, self.preferred_output_format)
                    
                    if converted_path and os.path.exists(converted_path):
                        with open(converted_path, 'rb') as converted_file:
                            converted_content = converted_file.read()
                        os.unlink(converted_path)
                        
                        conversion_message = f"Converted from {file_ext} to {self.preferred_output_format}"
                        return converted_content, conversion_message
                    else:
                        logger.warning(f"Failed to convert {file_ext}, using original format")
                        conversion_message = f"Conversion failed, using original {file_ext}"
                        return file_content, conversion_message
                
                else:
                    optimized_path = self._convert_audio_format(temp_file_path, 'mp3')
                    
                    if optimized_path and os.path.exists(optimized_path):
                        with open(optimized_path, 'rb') as optimized_file:
                            optimized_content = optimized_file.read()
                        
                        os.unlink(optimized_path)
                        
                        conversion_message = f"Optimized {file_ext} for speech recognition"
                        return optimized_content, conversion_message
                    else:
                        conversion_message = f"Using original {file_ext} format"
                        return file_content, conversion_message
                        
            finally:
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Error in audio validation/conversion: {str(e)}")
            return file_content, f"Error processing audio: {str(e)}"
    
    def get_supported_audio_formats(self) -> List[str]:
        """Get list of supported audio formats"""
        return self.supported_input_formats.copy()
    
    def is_audio_format_supported(self, filename: str) -> bool:
        """Check if audio format is supported"""
        file_ext = os.path.splitext(filename)[1].lower()
        return file_ext in self.supported_input_formats
    


    def detect_task_intent(self, message: str) -> Dict[str, Any]:
        """
        Detect if user message indicates intent to add a task
        
        Args:
            message: User's message
            
        Returns:
            Dictionary with detection result and parsed task details if applicable
        """
        try:
            system_prompt = """You are a task intent detector. 
Determine if the user message indicates they want to add/create a new task or reminder.
Response must be in JSON format: {"is_task": boolean, "confidence": float}
Examples:
- "Remind me to call John tomorrow" -> {"is_task": true, "confidence": 0.9}
- "How are you?" -> {"is_task": false, "confidence": 0.95}
- "Schedule a meeting with team" -> {"is_task": true, "confidence": 0.85}
- "What's on my calendar?" -> {"is_task": false, "confidence": 0.8}
"""
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.1,
                max_tokens=100
            )
            
            result = json.loads(response.choices[0].message.content.strip())
            return result
            
        except Exception as e:
            logger.error(f"Error in task intent detection: {str(e)}")
            return {"is_task": False, "confidence": 0.0}

    async def process_chat_message(
        self, 
        message: str,
        date_time: str,
        task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    ) -> Dict[str, Any]:
        """
        Process chat message with optional task context using OpenAI GPT

        Args:
            message: User's chat message
            task_context: Optional task context JSON (single dict or list of dicts)
            date_time: Current date and time in ISO format (e.g., "2025-07-24T14:18:36.514Z")
            
        Returns:
            Dictionary with response, success status, and optional task
        """
        try:

            intent_result = self.detect_task_intent(message)

            if intent_result.get("is_task", False) and intent_result.get("confidence", 0) > 0.7:
                result = await voice_assistant.process_voice_and_text(
                    transcribed_text=message,
                    date_time=date_time
                )
                return {
                    "response": "Your task is added",
                    "task": result.get("task", None)
                }
            
            current_date = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
            tomorrow_date = current_date + timedelta(days=1)
            
            # Updated system prompt to handle richer task responses
            system_prompt = f"""You are a helpful AI assistant with task management capabilities.
    Current date and time: {date_time}
    Today's date: {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A, %B %d, %Y')})
    Tomorrow's date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A, %B %d, %Y')})

    You help users manage their tasks and answer questions about their schedule, priorities, and workload. When you answer about tasks, use proper style and be helpful. 

    IMPORTANT: Always respond in the following JSON format:
    {{"response": "Your helpful response here"}}

    When listing tasks for the user, you should mention all relevant tasks scheduled for today. Provide not only the task name but also relevant details, such as the time, priority, and a suggestion for how to handle conflicting or upcoming tasks.

    You can also provide actionable insights, such as:
    - Whether the user has any upcoming tasks today.
    - If there are tasks in conflict with each other (overlapping times).
    - A summary of any important tasks the user should focus on today.

    Do not simply repeat the task context as-is. Always enrich your response with useful suggestions or insights. 

    Guidelines:
    - The date field in tasks means the date when the task should be done.
    - The time field in tasks is in 24-hour format (GMT).
    - Be concise and helpful.
    - Reference specific tasks when relevant.
    - Provide actionable insights.
    - Help prioritize and organize tasks
    """
            
            if task_context:
                system_prompt += f"""

    You have access to the following tasks:
    {json.dumps(task_context, indent=2)}

    Use this task information to provide relevant and contextual responses. You can reference specific tasks, help with scheduling, provide reminders, or answer questions related to the tasks.

    Guidelines:
    - The date field in tasks means the date when the task should be done
    - The time field in tasks is in 24-hour format (GMT)
    - Be concise and helpful
    - Reference specific tasks when relevant
    - Provide actionable insights
    - Help prioritize and organize tasks

    IMPORTANT: Always respond in the following JSON format:
    {{"response": "Your helpful response here"}}
    """

            
            response = self.client.chat.completions.create(
                model="gpt-4-turbo",  
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content.strip()

            try:
                if ai_response.strip().startswith('{') and ai_response.strip().endswith('}'):
                    parsed_response = json.loads(ai_response)
                    return {
                        "response": parsed_response.get("response", ai_response),
                        "task": None
                    }
                else:
                    return {
                        "response": ai_response,
                        "task": None
                    }
            except json.JSONDecodeError:
                return {
                    "response": ai_response,
                    "task": None
                }
            
        except openai.OpenAIError as e:
            return {
                "response": f"I apologize, but I'm experiencing some technical difficulties with the AI service: {str(e)}",
                "task": {}
            }
        except Exception as e:
            return {
                "response": f"I apologize, but I encountered an error while processing your message: {str(e)}",
                "task": {}
            }
