from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Conversation, Message
from ..schemas import ChatRequest, ChatResponse, ConversationHistoryResponse, MessageResponse
from ..services.rag import get_rag_response

router = APIRouter(prefix="/chat", tags=["chat"])

def get_or_create_conversation(document_id: int, db: Session) -> Conversation:
    conversation = db.query(Conversation).filter(
        Conversation.document_id == document_id
    ).first()
    if not conversation:
        conversation = Conversation(document_id=document_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation

@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    conversation = get_or_create_conversation(request.document_id, db)

    # Store user message
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question
    )
    db.add(user_message)
    db.commit()

    # Get RAG response
    answer = get_rag_response(request.question, request.document_id)

    # Store assistant message
    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer
    )
    db.add(assistant_message)
    db.commit()

    return ChatResponse(
        answer=answer,
        document_id=request.document_id,
        conversation_id=conversation.id
    )

@router.get("/{document_id}/history", response_model=ConversationHistoryResponse)
def get_history(document_id: int, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(
        Conversation.document_id == document_id
    ).first()

    if not conversation:
        raise HTTPException(status_code=404, detail="No conversation found for this document")

    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()

    return ConversationHistoryResponse(
        conversation_id=conversation.id,
        document_id=document_id,
        messages=[MessageResponse.model_validate(m) for m in messages]
    )