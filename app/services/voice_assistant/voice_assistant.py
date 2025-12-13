import os
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import openai

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
            🔴 ABSOLUTE RULE: NEVER TRANSLATE THE USER'S TEXT 🔴
            
            YOUR TASK HAS TWO STEPS:

            STEP 1: FIX MINOR TRANSCRIPTION ERRORS (SAME LANGUAGE ONLY)
            - Keep the EXACT SAME language as the input
            - Only fix obvious typos (e.g., "auframen" → "aufräumen")
            - DO NOT TRANSLATE to any other language
            - If text is in German, keep it German
            - If text is in English, keep it English

            STEP 2: CREATE TASK IN THE SAME LANGUAGE AS INPUT
            
            🚨 CRITICAL LANGUAGE RULES - READ CAREFULLY 🚨
            
            LANGUAGE PRIORITY: GERMAN and ENGLISH (detect which one the user is using)
            
            DETECTION RULES:
            1. Check if the input contains German words (ich, mich, zimmer, aufräumen, morgen, heute, etc.)
               → If YES, the PRIMARY language is GERMAN
            2. Check if the input contains English words (remind, tomorrow, today, meeting, call, etc.)
               → If YES and no German words, the PRIMARY language is ENGLISH
            3. For mixed inputs, count which language has MORE words
            
            🔴 MANDATORY: Title and Description MUST be in the PRIMARY language 🔴
            
            EXAMPLES:
            
            ✅ CORRECT German Task:
            Input: "zimmer aufräumen"
            Output: {{
                "title": "Zimmer aufräumen",
                "description": "Das Zimmer aufräumen und ordnen",
                ...
            }}
            
            ❌ WRONG (NEVER DO THIS):
            Input: "zimmer aufräumen"
            Output: {{
                "title": "Room tidying",  ← WRONG! This is translated!
                "description": "Tidying up the room",  ← WRONG! This is translated!
                ...
            }}
            
            ✅ CORRECT English Task:
            Input: "tidy up room"
            Output: {{
                "title": "Tidy up room",
                "description": "Clean and organize the room",
                ...
            }}
            
            ✅ CORRECT Mixed Language (German primary):
            Input: "ich muss ein meeting vorbereiten"
            Output: {{
                "title": "Meeting vorbereiten",
                "description": "Ein Meeting vorbereiten und planen",
                ...
            }}
            
            🔴 IF INPUT IS GERMAN → KEEP EVERYTHING GERMAN 🔴
            🔴 IF INPUT IS ENGLISH → KEEP EVERYTHING ENGLISH 🔴
            
            FIELD INSTRUCTIONS:
            - title: Task title in PRIMARY language (NO TRANSLATION!)
                    * Remove temporal words like "tomorrow", "morgen", "today", "heute"
                    * Example: "zimmer aufräumen morgen" → title: "Zimmer aufräumen"
            - description: Detailed description in PRIMARY language (NO TRANSLATION!)
                         * Example for German: "Das Zimmer aufräumen und in Ordnung bringen"
                         * Example for English: "Clean and organize the room"
            - priority: "high", "medium", or "low" (English)
            - date: YYYY-MM-DD format:
              * "tomorrow"/"morgen" = {tomorrow_date.strftime('%Y-%m-%d')}
              * "today"/"heute" = {current_date.strftime('%Y-%m-%d')}
              * "next week"/"nächste woche" = +7 days
              * If no date mentioned, use null
            - time: HH:MM format (24-hour). If no specific time, use null
            - category: Task category in English (work, personal, health, shopping, meeting, reminder)
            - tags: Keywords in English
            
            Current date and time: {date_time}
            Today: {current_date.strftime('%Y-%m-%d')}
            Tomorrow: {tomorrow_date.strftime('%Y-%m-%d')}
            
            Text to analyze: "{transcribed_text}"
            
            Respond with ONLY a JSON object.
            
            German Input Example:
            Input: "zimmer aufräumen"
            {{
                "title": "Zimmer aufräumen",
                "description": "Das Zimmer aufräumen und in Ordnung bringen",
                "priority": "medium",
                "date": null,
                "time": null,
                "category": "personal",
                "tags": ["room", "cleaning"]
            }}
            
            German Input with Context:
            Input: "Ich muss die bank über die neue transaktion informieren"
            {{
                "title": "Bank über neue Transaktion informieren",
                "description": "Die Bank über die neue Transaktion informieren",
                "priority": "medium",
                "date": null,
                "time": null,
                "category": "work",
                "tags": ["bank", "transaction"]
            }}
            
            English Input Example:
            Input: "I need to call the doctor tomorrow about my appointment"
            {{
                "title": "Call the doctor about appointment",
                "description": "Need to call the doctor to discuss the appointment",
                "priority": "medium",
                "date": "{tomorrow_date.strftime('%Y-%m-%d')}",
                "time": null,
                "category": "health",
                "tags": ["call", "doctor", "appointment"]
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": "You are a multilingual task extraction assistant. You MUST preserve the original language of the user's input. NEVER translate German to English or English to German. Extract task information while keeping title and description in the same language as the input."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            response_text = response.choices[0].message.content.strip()
            
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                task_data = json.loads(json_str)
            else:
                raise ValueError("No valid JSON found in AI response")
            
            task_data["id"] = str(uuid.uuid4())
            task_data["status"] = "pending"

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
        
        if "date" in task_data and task_data["date"]:
            try:
                datetime.strptime(task_data["date"], '%Y-%m-%d')
            except ValueError:
                try:
                    parsed_date = datetime.fromisoformat(task_data["date"].replace('Z', '+00:00'))
                    task_data["date"] = parsed_date.strftime('%Y-%m-%d')
                except:
                    task_data["date"] = None
        
        if "due_date" in task_data:
            if task_data["due_date"] and not task_data.get("date"):
                try:
                    parsed_date = datetime.fromisoformat(task_data["due_date"].replace('Z', '+00:00'))
                    task_data["date"] = parsed_date.strftime('%Y-%m-%d')
                except:
                    pass
            del task_data["due_date"]
        
        return task_data