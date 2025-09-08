from pydantic import BaseModel
class GreetingsRequest(BaseModel):
    user_id: str
    user_name:str
