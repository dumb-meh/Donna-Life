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

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        # Configure OpenAI API
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Supported audio formats for conversion
        self.supported_input_formats = [
            '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', 
            '.mp4', '.avi', '.mov', '.mkv', '.webm', '.3gp', '.amr'
        ]
        self.preferred_output_format = 'mp3'  # Efficient and widely supported
    
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
            # Load audio file
            audio = AudioSegment.from_file(input_file_path)
            
            # Optimize audio settings for speech recognition
            # Convert to mono (single channel) for better speech recognition
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Ensure sample rate is appropriate (16kHz is optimal for speech)
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
            
            # Create output file path
            base_name = os.path.splitext(input_file_path)[0]
            output_file_path = f"{base_name}_converted.{output_format}"
            
            # Export with optimized settings
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
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower()
            
            # Create temporary file for original audio
            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            conversion_message = f"Original format: {file_ext}"
            
            try:
                # Check if format conversion is needed
                if file_ext not in ['.mp3', '.wav', '.flac', '.m4a', '.ogg']:
                    logger.info(f"Converting unsupported format {file_ext} to {self.preferred_output_format}")
                    
                    # Convert to preferred format
                    converted_path = self._convert_audio_format(temp_file_path, self.preferred_output_format)
                    
                    if converted_path and os.path.exists(converted_path):
                        # Read converted file
                        with open(converted_path, 'rb') as converted_file:
                            converted_content = converted_file.read()
                        
                        # Clean up converted file
                        os.unlink(converted_path)
                        
                        conversion_message = f"Converted from {file_ext} to {self.preferred_output_format}"
                        return converted_content, conversion_message
                    else:
                        logger.warning(f"Failed to convert {file_ext}, using original format")
                        conversion_message = f"Conversion failed, using original {file_ext}"
                        return file_content, conversion_message
                
                else:
                    # File is already in a good format, but let's optimize it
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
                # Clean up original temporary file
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
        
        # Common date patterns
        text_lower = text.lower()
        
        if "today" in text_lower:
            return current_date
        elif "tomorrow" in text_lower:
            return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        elif "next week" in text_lower:
            return (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        elif "next month" in text_lower:
            return (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        
        # Try to extract specific date formats
        # Pattern for DD/MM/YYYY
        date_pattern = r"(\d{1,2})/(\d{1,2})/(\d{4})"
        match = re.search(date_pattern, text)
        if match:
            day, month, year = match.groups()
            try:
                parsed_date = datetime(int(year), int(month), int(day))
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                pass
        
        # Default to today if no date found
        return current_date
    
    def filter_tasks_by_relevance(self, tasks: List[Dict[str, Any]], user_message: str) -> List[Dict[str, Any]]:
        """Filter tasks based on user message context"""
        if not tasks:
            return []
        
        message_lower = user_message.lower()
        filtered_tasks = []
        
        # Date-based filtering - support both 'date' and 'due_date' fields
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
            # Current week
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            end_of_week = start_of_week + timedelta(days=6)
            start_date = start_of_week.strftime("%Y-%m-%d")
            end_date = end_of_week.strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) and start_date <= get_task_date(task) <= end_date]
        
        # Priority-based filtering
        elif any(keyword in message_lower for keyword in ["urgent", "high priority", "important"]):
            filtered_tasks = [task for task in tasks if task.get("priority") == "high"]
        
        elif any(keyword in message_lower for keyword in ["low priority", "least important"]):
            filtered_tasks = [task for task in tasks if task.get("priority") == "low"]
        
        # Status-based filtering
        elif any(keyword in message_lower for keyword in ["pending", "not started", "todo"]):
            filtered_tasks = [task for task in tasks if task.get("status") == "pending"]
        
        elif any(keyword in message_lower for keyword in ["in progress", "working on", "current"]):
            filtered_tasks = [task for task in tasks if task.get("status") == "in progress"]
        
        elif any(keyword in message_lower for keyword in ["completed", "done", "finished"]):
            filtered_tasks = [task for task in tasks if task.get("status") == "completed"]
        
        # Overdue tasks - support both 'date' and 'due_date' fields
        elif any(keyword in message_lower for keyword in ["overdue", "late", "past due"]):
            today = datetime.now().strftime("%Y-%m-%d")
            filtered_tasks = [task for task in tasks if get_task_date(task) and get_task_date(task) < today and task.get("status") != "completed"]
        
        # Keyword-based filtering (search in title and description)
        elif any(keyword in message_lower for keyword in ["about", "regarding", "related to"]):
            # Extract potential keywords after these phrases
            keywords = []
            for phrase in ["about", "regarding", "related to"]:
                if phrase in message_lower:
                    start_idx = message_lower.find(phrase) + len(phrase)
                    remaining_text = message_lower[start_idx:].strip()
                    # Take the next few words as potential keywords
                    potential_keywords = remaining_text.split()[:3]  # Take up to 3 words
                    keywords.extend(potential_keywords)
            
            if keywords:
                filtered_tasks = []
                for task in tasks:
                    title = task.get("title", "").lower()
                    description = task.get("description", "").lower()
                    if any(keyword in title or keyword in description for keyword in keywords):
                        filtered_tasks.append(task)
        
        # If no specific filters applied, use smart defaults
        if not filtered_tasks:
            # If user asks about schedule, meetings, or tasks, show relevant tasks
            if any(keyword in message_lower for keyword in ["schedule", "agenda", "calendar", "tasks", "what do i have", "meeting", "meetings", "appointments"]):
                # For meeting-related queries, show a broader range including recent past and future
                if any(keyword in message_lower for keyword in ["meeting", "meetings", "appointment", "appointments"]):
                    # Show meetings from yesterday to next week
                    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                    filtered_tasks = [task for task in tasks if get_task_date(task) and yesterday <= get_task_date(task) <= end_date]
                    
                    # Filter for meeting-related tasks
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
                    # For general schedule queries, show upcoming tasks (next 7 days)
                    start_date = datetime.now().strftime("%Y-%m-%d")
                    end_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                    filtered_tasks = [task for task in tasks if get_task_date(task) and start_date <= get_task_date(task) <= end_date]
                
                # Limit to most relevant tasks (high priority first, then by due date)
                filtered_tasks = sorted(filtered_tasks, key=lambda x: (
                    0 if x.get("priority") == "high" else 1 if x.get("priority") == "medium" else 2,
                    get_task_date(x) or "9999-12-31"
                ))[:10]  # Limit to 10 most relevant tasks
            
            # For general questions, provide a small context of today's and tomorrow's tasks
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
                
                today_tasks = [task for task in tasks if get_task_date(task) == today][:3]
                tomorrow_tasks = [task for task in tasks if get_task_date(task) == tomorrow][:3]
                
                filtered_tasks = today_tasks + tomorrow_tasks
        
        # Ensure we don't send too many tasks (limit to 15 for performance)
        if len(filtered_tasks) > 15:
            # Prioritize by due date and priority - support both date fields
            filtered_tasks = sorted(filtered_tasks, key=lambda x: (
                get_task_date(x) or "9999-12-31",
                0 if x.get("priority") == "high" else 1 if x.get("priority") == "medium" else 2
            ))[:15]
        
        logger.info(f"Filtered {len(tasks)} tasks to {len(filtered_tasks)} relevant tasks based on query: '{user_message[:50]}...'")
        return filtered_tasks
    
    def preprocess_task_context(self, task_context: Union[Dict[str, Any], List[Dict[str, Any]]], user_message: str) -> List[Dict[str, Any]]:
        """Preprocess and filter task context based on user message"""
        # Convert single dict to list for consistent processing
        if isinstance(task_context, dict):
            tasks = [task_context]
        else:
            tasks = task_context
        
        # Filter tasks based on relevance to user message
        filtered_tasks = self.filter_tasks_by_relevance(tasks, user_message)
        
        return filtered_tasks

    async def process_chat_message(
        self, 
        message: str, 
        time_zone: str,
        task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    ) -> Dict[str, Any]:
        """
        Process chat message with optional task context using OpenAI GPT
        
        Args:
            message: User's chat message
            time_zone: User's timezone (e.g., "+05:30", "-08:00", "+00:00")
            task_context: Optional task context JSON (single dict or list of dicts)
            
        Returns:
            Dictionary with response and success status
        """
        try:
            # Build the system prompt with filtered task context if provided
            current_datetime = datetime.now()
            
            system_prompt = f"""You are a helpful AI assistant with task management capabilities.
Current date and time (GMT): {current_datetime.strftime("%Y-%m-%d %H:%M:%S")} ({current_datetime.strftime("%A, %B %d, %Y at %H:%M")})
User's timezone: GMT{time_zone}
Note: Convert all times to the user's timezone (GMT{time_zone}) when displaying times or dates to the user.

You help users manage their tasks and answer questions about their schedule, priorities, and workload.

IMPORTANT: Always respond in the following JSON format:
{{"response": "Your helpful response here", "user_msg": "The corrected user message (fix any errors or keep as-is)"}}"""
            
            if task_context:
                # Preprocess and filter tasks based on user message
                filtered_tasks = self.preprocess_task_context(task_context, message)
                
                if filtered_tasks:
                    system_prompt += f"""

You have access to the following relevant tasks:
{json.dumps(filtered_tasks, indent=2)}

Use this task information to provide relevant and contextual responses. You can reference specific tasks, help with scheduling, provide reminders, or answer questions related to the tasks. Focus on the most relevant information for the user's query.

Guidelines:
- All times in the system are in GMT. Convert to user's timezone when displaying to user.
- The date field in tasks means the date when the task should be done
- The time field in tasks is in 24-hour format (GMT)
- Be concise and helpful
- Reference specific tasks when relevant
- Provide actionable insights
- Help prioritize and organize tasks
- Suggest time management strategies when appropriate
- When showing times to the user, convert from GMT to their timezone (GMT{time_zone})
- IMPORTANT: Always respond in the following JSON format:

{{"response": "Your helpful response here", "user_msg": "The corrected user message (fix any errors or keep as-is)"}}

Example response:
{{"response": "Your schedule for today includes the task 'Fix minor bugs' which has already been completed. If you have any other tasks or need assistance with planning your day, feel free to let me know!", "user_msg": "What's my schedule for today?"}}
"""
                else:
                    system_prompt += """

No tasks match your current query, but I'm here to help with general questions and task management advice.

IMPORTANT: Always respond in the following JSON format:
{"response": "Your helpful response here", "user_msg": "The corrected user message (fix any errors or keep as-is)"}
"""
            
            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            ai_response = response.choices[0].message.content.strip()
            
            # Try to parse the AI response as JSON to extract structured data
            try:
                # Check if the response is in JSON format
                if ai_response.strip().startswith('{') and ai_response.strip().endswith('}'):
                    parsed_response = json.loads(ai_response)
                    return {
                        "response": parsed_response.get("response", ai_response),
                        "user_msg": parsed_response.get("user_msg", message),
                    }
                else:
                    # If not JSON, return the response as-is
                    return {
                        "response": ai_response,
                        "user_msg": message,
                    }
            except json.JSONDecodeError:
                # If JSON parsing fails, return the response as-is
                return {
                    "response": ai_response,
                    "user_msg": message,
                }
            
        except openai.OpenAIError as e:
            return {
                "response": f"I apologize, but I'm experiencing some technical difficulties with the AI service: {str(e)}",
                "user_msg": message,
            }
        except Exception as e:
            return {
                "response": f"I apologize, but I encountered an error while processing your message: {str(e)}",
                "user_msg": message,
            }
