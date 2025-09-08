from pathlib import Path
from openai import OpenAI
import asyncio
class Greetings:
    def __init__(self):
        self.client = OpenAI()
        
    

    async def convert_text_to_speech_and_save(self, user_id: str, user_name: str) -> list:
        """
        Converts six greetings to speech, saves them as greetings/{user_id}/{greeting_no}.mp3,
        and returns their public URLs.
        """
        greetings = [
            f"Hi {user_name} what's on the agenda? ",
            "Hello Boss, what's on the list?",
            "Hi Chief, what's the mission?",
            f"Hello {user_name}, what's the game plan?",
            f"Let's go {user_name}",
            f"Any tasks today {user_name}"
        ]

        BASE_DIR = Path(__file__).resolve().parents[2]
        folder_path = BASE_DIR / "greetings" / user_id
        folder_path.mkdir(parents=True, exist_ok=True)

        async def write_audio_to_file(greeting_text, greeting_no):
            speech_file_path = folder_path / f"{greeting_no}.mp3"
            def sync_write():
                with self.client.audio.speech.with_streaming_response.create(
                    model="gpt-4o-mini-tts",
                    voice="coral",
                    input=greeting_text,
                    instructions="Speak in a cheerful and positive tone."
                ) as response:
                    response.stream_to_file(str(speech_file_path))
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, sync_write)
            return greeting_no

        tasks = [write_audio_to_file(greetings[i], i+1) for i in range(6)]
        await asyncio.gather(*tasks)

        base_url = f"http://206.162.244.131:8033/greetings/{user_id}"
        urls = [f"{base_url}/{i+1}.mp3" for i in range(6)]
        return urls
