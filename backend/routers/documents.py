from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Document
from ..schemas import DocumentResponse
from ..services.extractor import extract_text
from ..services.embedder import chunk_and_embed
from typing import List

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt"
}

@router.get("/", response_model=List[DocumentResponse])
def get_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()

@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and TXT files are allowed")

    file_type = ALLOWED_TYPES[file.content_type]
    file_bytes = await file.read()

    text = extract_text(file_bytes, file_type)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from document")

    document = Document(filename=file.filename, file_type=file_type, status="embedding")
    db.add(document)
    db.commit()
    db.refresh(document)

    chunk_and_embed(text, document.id)

    document.status = "ready"
    db.commit()
    db.refresh(document)

    return document