from pydantic import BaseModel
from typing import Optional, Dict, Any, List, Union

class ChatTextRequest(BaseModel):
    message: str
    task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    date_time: str

class ChatVoiceRequest(BaseModel):
    task_context: Optional[Union[Dict[str, Any], List[Dict[str, Any]]]] = None
    date_time: str

class ChatResponse(BaseModel):
    response: str
    task:Union[Dict[str, Any], List[Dict[str, Any]], Any]