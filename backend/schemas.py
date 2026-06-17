from pydantic import BaseModel
from datetime import datetime
from typing import List

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    document_id: int
    question: str

class ChatResponse(BaseModel):
    answer: str
    document_id: int
    conversation_id: int

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True

class ConversationHistoryResponse(BaseModel):
    conversation_id: int
    document_id: int
    messages: List[MessageResponse]