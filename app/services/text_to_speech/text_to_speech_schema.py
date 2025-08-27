from pydantic import BaseModel
class TextToSpeechRequest(BaseModel):
    text: str
    greeting_no: int
    user_id: str
