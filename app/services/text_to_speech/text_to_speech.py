from pathlib import Path
from openai import OpenAI
import asyncio

class TextToSpeechService:
    def __init__(self):
        self.client = OpenAI()

    async def convert_text_to_speech_and_save(self, text: str, user_id: str, greeting_no: int) -> str:
        """
        Converts text to speech and saves it to greetings/{user_id}/{greeting_no}.mp3
        Returns the file path as a string.
        """

        # Build the file path
        folder_path = Path("greetings") / user_id
        folder_path.mkdir(parents=True, exist_ok=True)
        speech_file_path = folder_path / f"{greeting_no}.mp3"

        def write_audio_to_file():
            with self.client.audio.speech.with_streaming_response.create(
                model="gpt-4o-mini-tts",
                voice="coral",
                input=text,
                instructions="Speak in a cheerful and positive tone."
            ) as response:
                response.stream_to_file(str(speech_file_path))

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_audio_to_file)

        return str(speech_file_path)
