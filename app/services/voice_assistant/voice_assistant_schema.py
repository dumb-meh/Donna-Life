from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class VoiceAssistantRequest(BaseModel):
    pass  # No fields needed since we only accept file upload
    
class TextRequest(BaseModel):
    text: str 
    
class TaskItem(BaseModel):
    id: str
    title: str
    description: str
    priority: str  # high, medium, low
    date: Optional[str] = None  # Date when the task should be done (YYYY-MM-DD format)
    time: Optional[str] = None  # Time when the task should be done (HH:MM format)
    category: Optional[str] = None
    status: str = "pending"  # pending, in_progress, completed
    tags: Optional[List[str]] = []
    
class VoiceAssistantResponse(BaseModel):
    task: Optional[TaskItem] = None
    success: bool
    message: Optional[str] = None