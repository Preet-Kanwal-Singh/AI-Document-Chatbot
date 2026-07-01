from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Document, User, Conversation, Message
from ..schemas import DocumentResponse
from ..services.extractor import extract_text
from ..services.embedder import chunk_and_embed
from ..auth import get_current_user
from ..vector_store import delete_chunks
from typing import List
import os
import tempfile
from ..services.video import process_video_upload


router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    # Documents
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    # Audio — browsers send slightly different MIME types for the same format
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/wave": "wav",
    "audio/x-wav": "wav",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/ogg": "ogg",
    "audio/webm": "webm",
    "audio/flac": "flac",
    "audio/x-flac": "flac",
}

AUDIO_FILE_TYPES = {"mp3", "wav", "m4a", "ogg", "webm", "flac"}
MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024  # Groq API hard limit

ALLOWED_VIDEO_TYPES = {
    "video/mp4": "video",
    "video/mpeg": "video",
    "video/quicktime": "video",  # .mov
    "video/avi": "video",
    "video/x-flv": "video",
    "video/mpg": "video",
    "video/webm": "video",
    "video/wmv": "video",
    "video/3gpp": "video",
}

MAX_VIDEO_SIZE_BYTES = 300 * 1024 * 1024  # 300MB
VIDEO_CHUNK_SIZE = 1024 * 1024  # read 1MB at a time, never hold the whole file in RAM


@router.get("/", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Supported formats: PDF, DOCX, TXT, MP3, WAV, M4A, OGG, FLAC",
        )

    file_type = ALLOWED_TYPES[file.content_type]
    file_bytes = await file.read()

    if file_type in AUDIO_FILE_TYPES and len(file_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Audio files must be under 25MB")

    text = extract_text(file_bytes, file_type, file.filename, file.content_type)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract content from file")

    document = Document(
        filename=file.filename,
        file_type=file_type,
        status="embedding",
        user_id=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    chunk_and_embed(text, document.id)

    document.status = "ready"
    db.commit()
    db.refresh(document)

    return document

@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document or document.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete messages → conversations → document (order matters for FK constraints)
    conversations = db.query(Conversation).filter(
        Conversation.document_id == document_id
    ).all()
    for conv in conversations:
        db.query(Message).filter(Message.conversation_id == conv.id).delete()
    db.query(Conversation).filter(Conversation.document_id == document_id).delete()

    # Remove chunks from ChromaDB
    delete_chunks(document_id)

    db.delete(document)
    db.commit()

async def _save_upload_streaming(file: UploadFile, max_bytes: int) -> str:
    """Stream the upload to a temp file on disk, checking size as we go.
    Aborts early on oversized files instead of waiting for the full upload first."""
    total = 0
    fd, temp_path = tempfile.mkstemp(suffix=f"_{file.filename}")
    try:
        with os.fdopen(fd, "wb") as out:
            while chunk := await file.read(VIDEO_CHUNK_SIZE):
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Video exceeds the {max_bytes // (1024 * 1024)}MB limit",
                    )
                out.write(chunk)
    except HTTPException:
        os.unlink(temp_path)
        raise
    return temp_path


@router.post("/upload-video", response_model=DocumentResponse, status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    temp_path = await _save_upload_streaming(file, MAX_VIDEO_SIZE_BYTES)

    try:
        document = Document(
            filename=file.filename,
            file_type="video",
            status="processing",
            user_id=current_user.id,
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        background_tasks.add_task(process_video_upload, document.id, temp_path)

    except Exception:
        # Anything failing between temp-file creation and successfully
        # scheduling the background task would otherwise leak the file
        # on disk with no reference to it anywhere.
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise

    return document

