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
            ⚠️ CRITICAL: YOU MUST PRESERVE THE ORIGINAL LANGUAGE OF THE INPUT TEXT ⚠️
            
            YOUR TASK HAS TWO STEPS:

            STEP 1: FIX ANY TRANSCRIPTION ERRORS IN THE INPUT TEXT
            - Keep the EXACT SAME language as the input - DO NOT TRANSLATE
            - Fix any obvious transcription errors (especially with numbers, dates, times)
            - Maintain the original meaning and intent
            - If text mentions time (like 2:00 or 14:00), ensure it's properly formatted
            - Fix any word spacing issues
            - If the text is already correct, use it as is

            STEP 2: EXTRACT TASK INFORMATION FROM THE CORRECTED TEXT
            
            ⚠️ ABSOLUTE LANGUAGE PRESERVATION RULES ⚠️
            
            PRIMARY LANGUAGES: GERMAN and ENGLISH (highest priority)
            
            LANGUAGE DETECTION:
            1. Identify the PRIMARY language by counting content words (ignore filler words)
            2. The language with MORE MEANINGFUL WORDS is the PRIMARY language
            3. ALWAYS keep 'title' and 'description' in the PRIMARY language
            4. NEVER translate the title or description - even if they contain mixed languages
            5. Keep exact phrases and terminology from the original text
            
            Language Detection Examples:
            - "Ich muss die bank über die neue transaktion informieren, bitte schick die email" 
              → PRIMARY: German (11 German words vs 2 English) → Keep title/description in GERMAN
            - "Ich habe ein appointment tomorrow mit dem doctor" 
              → PRIMARY: German (5 German words vs 3 English) → Keep title/description in GERMAN  
            - "I need to call the Arzt tomorrow about my Termin"
              → PRIMARY: English (7 English words vs 2 German) → Keep title/description in ENGLISH
            - "Remind me morgen to buy Brot"
              → PRIMARY: English (3 English words vs 2 German) → Keep title/description in ENGLISH
            - "Erinner mich daran tomorrow to call"
              → PRIMARY: German (3 German words vs 3 English = tie, but starts with German) → Keep in GERMAN
            
            🚫 NEVER TRANSLATE THE TITLE OR DESCRIPTION 🚫
            
            FIELD INSTRUCTIONS:
            - title: Clear, concise task title (IN PRIMARY LANGUAGE - NO TRANSLATION!)
                    * DO NOT use temporal words like "tomorrow/morgen", "today/heute", "next week/nächste Woche"
                    * Focus on the action and object
            - description: Detailed description (IN PRIMARY LANGUAGE - NO TRANSLATION!)
                         * DO NOT use temporal words like "tomorrow/morgen", "today/heute"  
                         * Explain what needs to be done
            - priority: "high", "medium", or "low" (IN ENGLISH)
            - date: YYYY-MM-DD format (IN ENGLISH):
              * "tomorrow/morgen" = {tomorrow_date.strftime('%Y-%m-%d')}
              * "today/heute" = {current_date.strftime('%Y-%m-%d')}
              * "next week/nächste woche" = approximate to 7 days from today
              * If no date mentioned, use null
            - time: HH:MM format (24-hour). If no specific time, use null. NEVER use words like "morning/Morgen", "evening/Abend", "afternoon/Nachmittag", "night/Nacht"
            - category: Task category (IN ENGLISH): work, personal, health, shopping, meeting, reminder, etc.
            - tags: Relevant keywords (IN ENGLISH)
            
            Current date and time: {date_time}
            Today's date: {current_date.strftime('%Y-%m-%d')} ({current_date.strftime('%A, %B %d, %Y')})
            Tomorrow's date: {tomorrow_date.strftime('%Y-%m-%d')} ({tomorrow_date.strftime('%A, %B %d, %Y')})
            
            Text to analyze: "{transcribed_text}"
            
            Respond with ONLY a JSON object, no additional text.
            
            Example for German input:
            Input: "Ich muss die bank über die neue transaktion informieren, bitte schick die email"
            {{
                "title": "Bank über neue Transaktion informieren",
                "description": "Die Bank über die neue Transaktion informieren und Email schicken",
                "priority": "medium",
                "date": null,
                "time": null,
                "category": "work",
                "tags": ["bank", "transaction", "email"]
            }}
            
            Example for English input with some German words:
            Input: "I need to call the Arzt tomorrow about my Termin"
            {{
                "title": "Call the doctor about appointment",
                "description": "Need to call the doctor tomorrow to discuss the appointment",
                "priority": "medium",
                "date": "{tomorrow_date.strftime('%Y-%m-%d')}",
                "time": null,
                "category": "health",
                "tags": ["call", "doctor", "appointment"]
            }}
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts task information from text and returns it as JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
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