from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class Message(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)

class SessionCreate(BaseModel):
    user_id: Optional[str] = None

class SessionResponse(BaseModel):
    session_id: str
    created_at: datetime
    dataset_name: Optional[str] = None
    dataset_shape: Optional[List[int]] = None
    dataset_columns: Optional[List[str]] = None

class QueryRequest(BaseModel):
    text: str

class QueryResponse(BaseModel):
    answer: str
    table_data: Optional[List[Dict[str, Any]]] = None # Preview of DataFrame
    visualization_urls: List[str] = []
    messages: List[Message] # Updated conversation history
