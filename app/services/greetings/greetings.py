from pathlib import Path
from openai import OpenAI
import asyncio

class Greetings:
    def __init__(self):
        self.client = OpenAI()

    async def convert_text_to_speech_and_save(self, user_id: str, user_name: str) -> dict:
        """
        Converts greetings (English and German) to speech, saves them under:
        greetings/{user_id}/English/{n}.mp3 and greetings/{user_id}/German/{n}.mp3,
        and returns their public URLs in structured JSON.
        """
        greetings = {
            "English": [
                f"Hi {user_name} what's on the agenda?",
                "Hello Boss, what's on the list?",
                "Hi Chief, what's the mission?",
                f"Hello {user_name}, what's the game plan?",
                f"Let's go {user_name}",
                f"Any tasks today {user_name}?"
            ],
            "German": [
                f"Hi {user_name}, was steht auf dem Plan?",
                "Hallo Boss, was steht heute an?",
                "Hi Chef, was ist die Mission?",
                f"Hallo {user_name}, was ist der Plan?",
                f"Los geht’s, {user_name}!",
                f"Gibt es heute Aufgaben, {user_name}?"
            ]
        }

        BASE_DIR = Path(__file__).resolve().parents[2]
        base_url = f"http://206.162.244.131:8035/greetings/{user_id}"

        result = {"message": "Audio files saved", "filepaths": {}}

        async def write_audio_to_file(text: str, lang: str, index: int):
            folder_path = BASE_DIR / "greetings" / user_id / lang
            folder_path.mkdir(parents=True, exist_ok=True)
            speech_file_path = folder_path / f"{index}.mp3"

            def sync_write():
                with self.client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    voice="coral",
                    input=text,
                    instructions="Speak in a cheerful and positive tone."
                ) as response:
                    response.stream_to_file(str(speech_file_path))

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, sync_write)

            return f"{base_url}/{lang}/{index}.mp3"

        tasks = []
        for lang in greetings:
            for i, text in enumerate(greetings[lang], 1):
                tasks.append(write_audio_to_file(text, lang, i))

        urls = await asyncio.gather(*tasks)

        result["filepaths"] = {
            "German": urls[6:],  
            "English": urls[:6]  
        }

        return result
