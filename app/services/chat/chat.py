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

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        except:
            return False
    
    def _convert_audio_format(self, input_file_path: str, output_format: str = 'mp3') -> Optional[str]:
        """
        Convert audio file to specified format using pydub
        
        Args:
            input_file_path: Path to input audio file
            output_format: Target format (mp3, wav, etc.)
            
        Returns:
            Path to converted file or None if conversion failed
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
    
    def parse_date_from_text(self, text: str) -> str:
        """Parse date from natural language text"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        text_lower = text.lower()
        
        if "today" in text_lower:
            return current_date
        elif "tomorrow" in text_lower:
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "next week" in text_lower:
            return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "next month" in text_lower:
            return (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        date_pattern = r"(\d{1,2})/(\d{1,2})/(\d{4})"
        match = re.search(date_pattern, text)
        if match:
            day, month, year = match.groups()
            try:
                parsed_date = datetime(int(year), int(month), int(day))
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        return current_date
    
    def filter_tasks_by_relevance(self, tasks: List[Dict[str, Any]], user_message: str) -> List[Dict[str, Any]]:
        """Filter tasks based on user message context"""
        if not tasks:
            return []
        
        message_lower = user_message.lower()
        filtered_tasks = []
        
        def get_task_date(task):
            return task.get("date") or task.get("due_date")
        
        if any(keyword in message_lower for keyword in ["today", "today's"]):
            today = datetime.now().strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) == today]
        
        elif any(keyword in message_lower for keyword in ["tomorrow", "tomorrow's"]):
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) == tomorrow]
        
        elif any(keyword in message_lower for keyword in ["next week", "next 7 days", "upcoming week"]):
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) and start_date <= get_task_date(task) <= end_date]
        
        elif any(keyword in message_lower for keyword in ["this week", "week"]):
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = start_of_week.strftime("%Y-%m-%d")
            end_date = end_of_week.strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) and start_date <= get_task_date(task) <= end_date]
        
        elif any(keyword in message_lower for keyword in ["urgent", "high priority", "important"]):
            filtered_tasks = [task for task in tasks if task.get("priority") == "high"]
        
        elif any(keyword in message_lower for keyword in ["low priority", "least important"]):
            filtered_tasks = [task for task in tasks if task.get("priority") == "low"]
        
        elif any(keyword in message_lower for keyword in ["pending", "not started", "todo"]):
            filtered_tasks = [task for task in tasks if task.get("status") == "pending"]
        
        elif any(keyword in message_lower for keyword in ["in progress", "working on", "current"]):
            filtered_tasks = [task for task in tasks if task.get("status") == "in progress"]
        
        elif any(keyword in message_lower for keyword in ["completed", "done", "finished"]):
            filtered_tasks = [task for task in tasks if task.get("status") == "completed"]
        
        elif any(keyword in message_lower for keyword in ["overdue", "late", "past due"]):
            today = datetime.now().strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) and get_task_date(task) < today and task.get("status") != "completed"]
        
        elif any(keyword in message_lower for keyword in ["about", "regarding", "related to"]):
            
            keywords = []
            for phrase in ["about", "regarding", "related to"]:
                if phrase in message_lower:
                    start_idx = message_lower.find(phrase) + len(phrase)
                    remaining_text = message_lower[start_idx:].strip()
                    potential_keywords = remaining_text.split()[:3]  
                    keywords.extend(potential_keywords)
            
            if keywords:
                filtered_tasks = []
                for task in tasks:
                    title = task.get("title", "").lower()
                    description = task.get("description", "").lower()
                    if any(keyword in title or keyword in description for keyword in keywords):
                        filtered_tasks.append(task)
        
        if not filtered_tasks:
            if any(keyword in message_lower for keyword in ["schedule", "agenda", "calendar", "tasks", "what do i have", "meeting", "meetings", "appointments"]):

                if any(keyword in message_lower for keyword in ["meeting", "meetings", "appointment", "appointments"]):

                    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                    filtered_tasks = [task for task in tasks if get_task_date(task) and yesterday <= get_task_date(task) <= end_date]

                    meeting_keywords = ["meeting", "conference", "call", "appointment", "attendance", "conferencia"]
                    meeting_tasks = []
                    for task in filtered_tasks:
                        title = task.get("title", "").lower()
                        description = task.get("description", "").lower()
                        if any(keyword in title or keyword in description for keyword in meeting_keywords):
                            meeting_tasks.append(task)
                    
                    if meeting_tasks:
                        filtered_tasks = meeting_tasks
                else:
                    start_date = datetime.now().strftime("%Y-%m-%d")
                    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                    filtered_tasks = [task for task in tasks if get_task_date(task) and start_date <= get_task_date(task) <= end_date]
                
                filtered_tasks = sorted(filtered_tasks, key=lambda x: (
                    0 if x.get("priority") == "high" else 1 if x.get("priority") == "medium" else 2,
                    get_task_date(x) or "9999-12-31"
                ))[:10]  
            
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                today_tasks = [task for task in tasks if get_task_date(task) == today][:3]
                tomorrow_tasks = [task for task in tasks if get_task_date(task) == tomorrow][:3]
                
                filtered_tasks = today_tasks + tomorrow_tasks

        if len(filtered_tasks) > 15:
            
            filtered_tasks = sorted(filtered_tasks, key=lambda x: (
                get_task_date(x) or "9999-12-31",
                0 if x.get("priority") == "high" else 1 if x.get("priority") == "medium" else 2
            ))[:15]
        
        logger.info(f"Filtered {len(tasks)} tasks to {len(filtered_tasks)} relevant tasks based on query: '{user_message[:50]}...'")
        return filtered_tasks
    
    def preprocess_task_context(self, task_context: Union[Dict[str, Any], List[Dict[str, Any]]], user_message: str) -> List[Dict[str, Any]]:
        """Preprocess and filter task context based on user message"""
        
        if isinstance(task_context, dict):
            tasks = [task_context]
        else:
            tasks = task_context

        filtered_tasks = self.filter_tasks_by_relevance(tasks, user_message)
        
        return filtered_tasks

    async def process_chat_message(
        self, 
        message: str, 
        task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None,
        date_time: str = None
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
                    # Parse the input date_time to get today and tomorrow
                    current_date = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
                    tomorrow_date = current_date + timedelta(days=1)
                    
                    system_prompt = f"""You are a helpful AI assistant with task management capabilities.
        Current date and time: {date_time}
        Today's date: {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A, %B %d, %Y')})
        Tomorrow's date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A, %B %d, %Y')})

        You help users manage their tasks and answer questions. You can also detect when users want to create new tasks.

        TASK CREATION RULES:
        - If user wants to add/create a task, respond with "Your task is being added" and include task JSON
        - Task titles/descriptions stay in original language, other fields in English
        - Don't use "today", "tomorrow", "next week" in title/description - use specific details
        - Time format: HH:MM (24hr), use null if no specific time mentioned
        - Priority: "high", "medium", or "low" based on urgency
        - Date format: YYYY-MM-DD ("tomorrow" = {tomorrow_date.strftime('%Y-%m-%d')}, "today" = {current_date.strftime('%Y-%m-%d')})

        ALWAYS respond in JSON format:
        {{"response": "Your response", "user_msg": "Corrected user message", "task": null or task_object}}

        Task object format when creating tasks:
{{"id": "task_" + random_string, "title": "Task title", "description": "Description", "priority": "medium", "date": "YYYY-MM-DD", "time": "HH:MM", "category": "work/personal/etc", "status": "pending", "tags": ["tag1", "tag2"]}}

CRITICAL: For the "id" field, generate an actual UUID in format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx (like fb0a45db-a546-4aa6-8e4d-7f7cccf9a316). Do NOT use placeholder text - generate a real, unique UUID every time."""
                    if task_context:
                        filtered_tasks = self.preprocess_task_context(task_context, message)
                        
                        if filtered_tasks:
                            system_prompt += f"""

        You have access to these relevant tasks:
        {json.dumps(filtered_tasks, indent=2)}

        Use this information to provide contextual responses about schedules, priorities, and workload."""
                        else:
                            system_prompt += """

        No tasks match your current query, but I can help with general questions and task creation."""
                    
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": message}
                        ],
                        temperature=0.7,
                        max_tokens=600
                    )
                    
                    ai_response = response.choices[0].message.content.strip()

                    try:
                        if ai_response.strip().startswith('{') and ai_response.strip().endswith('}'):
                            parsed_response = json.loads(ai_response)
                            return {
                                "response": parsed_response.get("response", ai_response),
                                "user_msg": parsed_response.get("user_msg", message),
                                "task": parsed_response.get("task", None),
                                "success": True
                            }
                        else:
                            return {
                                "response": ai_response,
                                "user_msg": message,
                                "task": None,
                                "success": True
                            }
                    except json.JSONDecodeError:
                        return {
                            "response": ai_response,
                            "user_msg": message,
                            "task": None,
                            "success": True
                        }
                    
                except openai.OpenAIError as e:
                    return {
                        "response": f"I apologize, but I'm experiencing some technical difficulties with the AI service: {str(e)}",
                        "user_msg": message,
                        "task": None,
                        "success": False
                    }
                except Exception as e:
                    return {
                        "response": f"I apologize, but I encountered an error while processing your message: {str(e)}",
                        "user_msg": message,
                        "task": None,
                        "success": False
                    }