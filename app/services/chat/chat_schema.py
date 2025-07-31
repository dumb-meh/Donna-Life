from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union

class ChatTextRequest(BaseModel):
    message: str
    task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    time_zone: str

class ChatVoiceRequest(BaseModel):
    task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None

class ChatResponse(BaseModel):
    response: str
    user_msg: str