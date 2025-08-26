from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from fastapi import Form, UploadFile, File

class VoiceAssistantRequest(BaseModel):
    date_time: str
    
    @classmethod
    def as_form(cls, date_time: str = Form(...)):
        return cls(date_time=date_time)

    
class TextRequest(BaseModel):
    text: str 
    
class TaskItem(BaseModel):
    id: str
    title: str
    description: str
    priority: str  
    date: Optional[str] = None  
    time: Optional[str] = None 
    category: Optional[str] = None
    status: str = "pending" 
    tags: Optional[List[str]] = []
    
class VoiceAssistantResponse(BaseModel):
    task: Optional[TaskItem] = None
    success: bool
    message: Optional[str] = None