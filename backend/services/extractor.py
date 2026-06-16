import pdfplumber
from docx import Document
import io

def extract_text(file_bytes: bytes, file_type: str) -> str:
    if file_type == "pdf":
        return _extract_from_pdf(file_bytes)
    elif file_type == "docx":
        return _extract_from_docx(file_bytes)
    elif file_type == "txt":
        return file_bytes.decode("utf-8")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

def _extract_from_pdf(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def _extract_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])