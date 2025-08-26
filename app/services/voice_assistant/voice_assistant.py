import openai
import json
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()

class VoiceAssistantService:
    def __init__(self):
        # Configure OpenAI API
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
    
    async def process_voice_and_text(
        self, 
        transcribed_text: str,
        date_time: str
    ) -> Dict[str, Any]:
        """
        Process transcribed audio to create a task JSON
        
        Args:
            transcribed_text: Text from speech-to-text conversion
            date_time: Current date and time in ISO format (e.g., "2025-07-24T14:18:36.514Z")
            
        Returns:
            Dictionary containing task information
        """
        try:
            # Parse the input date_time to get today and tomorrow
            current_date = datetime.fromisoformat(date_time.replace('Z', '+00:00'))
            tomorrow_date = current_date + timedelta(days=1)
            
            # Create prompt for OpenAI to extract task information
            prompt = f"""
            YOU MUST BE PREPARED FOR MULTILINGUAL INPUTS. Your task has two steps:

            STEP 1: FIX ANY TRANSCRIPTION ERRORS IN THE INPUT TEXT
            - Keep the same language as the input
            - Fix any obvious transcription errors (especially with numbers, dates, times)
            - Maintain the original meaning and intent
            - If text mentions time (like 2:00 or 14:00), ensure it's properly formatted
            - Fix any word spacing issues
            - DO NOT translate to another language
            - If the text is already correct, use it as is

            STEP 2: EXTRACT TASK INFORMATION FROM THE CORRECTED TEXT
            THE OUTPUT JSON STRUCTURE AND FIELD NAMES WILL BE IN ENGLISH, BUT THE VALUES FOR 'title' AND 'description' MUST BE IN THE SAME LANGUAGE AS THE INPUT TEXT.
            ALL OTHER FIELD VALUES (priority, date, time, category, tags) SHOULD BE IN ENGLISH.DON'T USE TOMORROW, TODAY, NEXT WEEK, etc. IN THE TITLE OR DESCRIPTION.
            
            Current date and time: {date_time}
            Today's date: {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A, %B %d, %Y')})
            Tomorrow's date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A, %B %d, %Y')})
            
            Analyze the following text and extract task information to create a structured task JSON.
            The text might contain a task request, reminder, or action item.
            
            Text to analyze: "{transcribed_text}"
            
            Please extract and structure this information into a task with the following format:
            - title: A clear, concise title for the task (IN THE SAME LANGUAGE AS INPUT) NOTE: DON'T USE TOMORROW, TODAY, NEXT WEEK, etc. IN THE TITLE
            - description: Detailed description of what needs to be done (IN THE SAME LANGUAGE AS INPUT) NOTE: DON'T USE TOMORROW, TODAY, NEXT WEEK, etc. IN THE DESCRIPTION
            - priority: Determine if this is "high", "medium", or "low" priority based on urgency keywords (IN ENGLISH)
            - date: Extract any date mentions and convert to YYYY-MM-DD format. Common phrases:
              * "tomorrow" = {tomorrow_date.strftime('%Y-%m-%d')}
              * "today" = {current_date.strftime('%Y-%m-%d')}
              * "next week" = approximate to 7 days from today
              * If no date mentioned, leave as null
            - time: Extract any time mentions in HH:MM format (24 hr), if applicable. If no time mentioned, leave it as "null", MUST NOT SEND MORNING,EVENING, AFTERNOON, NIGHT, etc.
            - category: Categorize the task (work, personal, health, shopping, meeting, reminder, etc.) (IN ENGLISH)
            - tags: Extract relevant keywords as tags (IN ENGLISH)
            
            Respond with a JSON object only, no additional text.
            Example format for Multilingual input:
            {{
                "title":  সকাল ১০ টায় মিটিং",
                "description": "সকাল ১০ টায় প্রজেক্ট ম্যানেজারের সাথে মিটিং আছে",
                "priority": "medium",
                "date": "2025-07-24",
                "time": "10:00",
                "category": "work",
                "tags": ["meeting", "project", "manager"]
            }}
            
            Example format for English input:
            {{
                "title": "Call John about project meeting",
                "description": "Need to call John to discuss the upcoming project meeting details",
                "priority": "medium",
                "date": "2025-07-03",
                "time": "14:00",
                "category": "work",
                "tags": ["call", "meeting", "john", "project"]
            }}
            """
            
            # Get response from OpenAI
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts task information from text and returns it as JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean the response to extract JSON
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                task_data = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in AI response")
            
            # Add required fields
            task_data["id"] = str(uuid.uuid4())
            task_data["status"] = "pending"
            
            # Validate and clean data
            task_data = self._validate_task_data(task_data)
            
            return {
                "task": task_data,
                "success": True,
                "message": "Task successfully created from voice input using OpenAI"
            }
            
        except json.JSONDecodeError as e:
            return {
                "task": None,
                "success": False,
                "message": f"Failed to parse AI response as JSON: {str(e)}"
            }
        except openai.OpenAIError as e:
            return {
                "task": None,
                "success": False,
                "message": f"OpenAI API error: {str(e)}"
            }
        except Exception as e:
            return {
                "task": None,
                "success": False,
                "message": f"Error processing voice input: {str(e)}"
            }
    
    def _validate_task_data(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean task data"""
        # Ensure required fields exist
        if "title" not in task_data or not task_data["title"]:
            task_data["title"] = "Untitled Task"
        
        if "description" not in task_data:
            task_data["description"] = task_data.get("title", "No description")
        
        if "priority" not in task_data or task_data["priority"] not in ["high", "medium", "low"]:
            task_data["priority"] = "medium"
        
        if "category" not in task_data:
            task_data["category"] = "general"
        
        if "tags" not in task_data:
            task_data["tags"] = []
        
        # Validate date format (YYYY-MM-DD)
        if "date" in task_data and task_data["date"]:
            try:
                # Try to parse the date to validate format
                datetime.strptime(task_data["date"], '%Y-%m-%d')
            except ValueError:
                try:
                    # Try to parse ISO format and convert to date only
                    parsed_date = datetime.fromisoformat(task_data["date"].replace('Z', '+00:00'))
                    task_data["date"] = parsed_date.strftime('%Y-%m-%d')
                except:
                    task_data["date"] = None
        
        # Handle legacy due_date field if present
        if "due_date" in task_data:
            if task_data["due_date"] and not task_data.get("date"):
                try:
                    parsed_date = datetime.fromisoformat(task_data["due_date"].replace('Z', '+00:00'))
                    task_data["date"] = parsed_date.strftime('%Y-%m-%d')
                except:
                    pass
            # Remove due_date field
            del task_data["due_date"]
        
        return task_data