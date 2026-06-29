import pdfplumber
from docx import Document
from groq import Groq
import io
import os
from dotenv import load_dotenv

load_dotenv()

def extract_text(
    file_bytes: bytes,
    file_type: str,
    filename: str = "audio",
    content_type: str = "",
) -> str:
    if file_type == "pdf":
        return _extract_from_pdf(file_bytes)
    elif file_type == "docx":
        return _extract_from_docx(file_bytes)
    elif file_type == "txt":
        return file_bytes.decode("utf-8")
    elif file_type in ("mp3", "wav", "m4a", "ogg", "webm", "flac"):
        return _extract_from_audio(file_bytes, filename, content_type)
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


def _extract_from_audio(file_bytes: bytes, filename: str, content_type: str) -> str:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    transcription = client.audio.transcriptions.create(
        model="whisper-large-v3-turbo",
        file=(filename, io.BytesIO(file_bytes), content_type),
        response_format="verbose_json",
        timestamp_granularities=["segment"],
    )

    if not transcription.segments:
        return transcription.text

    lines = []
    for segment in transcription.segments:
        start = _format_timestamp(segment["start"])
        end = _format_timestamp(segment["end"])
        lines.append(f"[{start} - {end}] {segment['text'].strip()}")

    return "\n".join(lines)


def _format_timestamp(seconds: float) -> str:
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}:{secs:02d}"