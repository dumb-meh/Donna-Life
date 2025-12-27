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
            - Only fix obvious typos in the same language
            - DO NOT TRANSLATE to any other language
            - Preserve the original language completely

            STEP 2: CREATE TASK IN THE SAME LANGUAGE AS INPUT
            
            🚨 CRITICAL LANGUAGE RULES - READ CAREFULLY 🚨
            
            SUPPORTED LANGUAGES (PRIMARY PRIORITY):
            - Turkish (Türkçe)
            - English
            - German (Deutsch)
            
            
            SUPPORTED LANGUAGES (SECONDARY PRIORITY):
            - Arabic (العربية)
            - Urdu (اردو)
            
            ALL OTHER LANGUAGES: Also supported - preserve them as-is
            
            LANGUAGE DETECTION RULES:
            1. Detect the PRIMARY language of the user's input by identifying key words
            2. For mixed inputs, use the language that appears MOST in the text
            3. Common indicators:
               - Turkish: ben, bana, yarın, bugün, oda, toplantı, ara, etc.
               - English: I, me, tomorrow, today, room, meeting, call, etc.
               - German: ich, mich, morgen, heute, zimmer, besprechung, anrufen, etc.
               - Urdu: میں، مجھے، کل، آج، کمرہ، میٹنگ، etc.
               - Arabic: أنا، لي، غدا، اليوم، غرفة، اجتماع، etc.
            
            🔴 MANDATORY: Title and Description MUST be in the PRIMARY language 🔴
            
            EXAMPLES FOR DIFFERENT LANGUAGES:
            
            ✅ CORRECT Turkish Task:
            Input: "odayı temizle"
            Output: {{
                "title": "Odayı temizle",
                "description": "Odayı temizle ve düzenle",
                ...
            }}
            
            
            ✅ CORRECT German Task:
            Input: "zimmer aufräumen"
            Output: {{
                "title": "Zimmer aufräumen",
                "description": "Das Zimmer aufräumen und ordnen",
                ...
            }}
            
            ✅ CORRECT English Task:
            Input: "tidy up room"
            Output: {{
                "title": "Tidy up room",
                "description": "Clean and organize the room",
                ...
            }}
            
            ✅ CORRECT Arabic Task:
            Input: "نظف الغرفة"
            Output: {{
                "title": "نظف الغرفة",
                "description": "تنظيف وترتيب الغرفة",
                ...
            }}
            
            ❌ WRONG (NEVER DO THIS):
            Input: "odayı temizle" (Turkish)
            Output: {{
                "title": "Clean the room",  ← WRONG! This is translated to English!
                "description": "Clean and organize the room",  ← WRONG!
                ...
            }}
            
            🔴 PRESERVE THE ORIGINAL LANGUAGE IN TITLE AND DESCRIPTION 🔴
            
            FIELD INSTRUCTIONS:
            - title: Task title in PRIMARY language (NO TRANSLATION!)
                    * Remove temporal words in ANY language:
                      - English: "tomorrow", "today"
                      - German: "morgen", "heute"
                      - Turkish: "yarın", "bugün"
                      - Urdu: "کل", "آج"
                      - Arabic: "غدا", "اليوم"
                    * Example: "odayı yarın temizle" → title: "Odayı temizle"
            - description: Detailed description in PRIMARY language (NO TRANSLATION!)
                         * Turkish example: "Odayı temizle ve düzenle"
                         * German example: "Das Zimmer aufräumen und in Ordnung bringen"
                         * English example: "Clean and organize the room"
                         * Urdu example: "کمرہ صاف اور منظم کریں"
                         * Arabic example: "تنظيف وترتيب الغرفة"
            - priority: "high", "medium", or "low" (English)
            - date: YYYY-MM-DD format - detect temporal keywords in ANY language:
              * Tomorrow words: "tomorrow", "morgen", "yarın", "کل", "غدا" = {tomorrow_date.strftime('%Y-%m-%d')}
              * Today words: "today", "heute", "bugün", "آج", "اليوم" = {current_date.strftime('%Y-%m-%d')}
              * Next week words: "next week", "nächste woche", "gelecek hafta" = +7 days
              * If no date mentioned, use null
            - time: HH:MM format (24-hour). If no specific time, use null
            - category: Task category in English (work, personal, health, shopping, meeting, reminder)
            - tags: Keywords in English
            
            Current date and time: {date_time}
            Today: {current_date.strftime('%Y-%m-%d')}
            Tomorrow: {tomorrow_date.strftime('%Y-%m-%d')}
            
            Text to analyze: "{transcribed_text}"
            
            Respond with ONLY a JSON object.
            
            Turkish Input Example:
            Input: "odayı temizle"
            {{
                "title": "Odayı temizle",
                "description": "Odayı temizle ve düzenle",
                "priority": "medium",
                "date": null,
                "time": null,
                "category": "personal",
                "tags": ["room", "cleaning"]
            }}
            
            
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
                    {"role": "system", "content": "You are a multilingual task extraction assistant supporting Turkish, English, German, Urdu, Arabic, and all other languages. You MUST preserve the original language of the user's input. NEVER translate the task title or description. Extract task information while keeping title and description in the exact same language as the input."},
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