import os
import time

from google import genai
from google.genai import types

from ..database import SessionLocal
from ..models import Document
from .embedder import chunk_and_embed

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)

POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 5 * 60  # matches your answer — 5 min ceiling on Gemini processing

VIDEO_DESCRIPTION_PROMPT = """Watch this video and describe both what is shown on screen and what is said.

For visuals: describe slides, diagrams, on-screen text, demonstrations, charts, code, UI,
or any other visual content.

For audio: summarize what the speaker says, including key points, explanations, definitions,
and any important statements. Paraphrase rather than transcribing word-for-word.

Format your response as a series of timestamped entries, one per distinct moment or change:
[MM:SS] Visual: Description of what is shown on screen.
[MM:SS] Spoken: Summary of what the speaker explains at this point.

Be specific and detailed enough that someone who never watched the video could answer
questions about both its visual and spoken content from your description alone."""


class QuotaExceededError(Exception):
    """Raised when Gemini returns a rate-limit/quota error — signals 'don't retry'."""
    pass


def _is_quota_error(exc: Exception) -> bool:
    # The Gemini SDK surfaces rate-limit/quota errors as 429s; the message
    # text is the most reliable signal available without inspecting SDK
    # internals that could change between versions.
    message = str(exc).lower()
    return "429" in message or "quota" in message or "rate limit" in message


def _upload_and_wait_for_active(temp_path: str):
    uploaded_file = client.files.upload(file=temp_path)

    elapsed = 0
    while uploaded_file.state.name == "PROCESSING":
        if elapsed >= POLL_TIMEOUT_SECONDS:
            raise TimeoutError(
                f"Gemini file processing did not complete within {POLL_TIMEOUT_SECONDS}s"
            )
        time.sleep(POLL_INTERVAL_SECONDS)
        elapsed += POLL_INTERVAL_SECONDS
        uploaded_file = client.files.get(name=uploaded_file.name)

    if uploaded_file.state.name == "FAILED":
        raise RuntimeError("Gemini failed to process the uploaded video file")

    return uploaded_file


def _describe_video(uploaded_file) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=[uploaded_file, VIDEO_DESCRIPTION_PROMPT],
        )
    except Exception as exc:
        if _is_quota_error(exc):
            raise QuotaExceededError(str(exc)) from exc
        raise
    return response.text


def _run_video_pipeline(document_id: int, temp_path: str) -> None:
    uploaded_file = _upload_and_wait_for_active(temp_path)
    description_text = _describe_video(uploaded_file)

    if not description_text or not description_text.strip():
        raise RuntimeError("Gemini returned an empty description for this video")

    chunk_and_embed(description_text, document_id)


def process_video_upload(document_id: int, temp_path: str, is_retry: bool = False) -> None:
    db = SessionLocal()
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            return

        try:
            _run_video_pipeline(document_id, temp_path)
            document.status = "ready"
            db.commit()

        except QuotaExceededError as exc:
            # Retrying immediately won't help — quota resets on Gemini's
            # schedule, not ours. Fail fast instead of burning the retry.
            document.status = "failed"
            document.error_message = "Gemini API quota exceeded. Please try again later."
            db.commit()

        except Exception as exc:
            if not is_retry:
                db.close()
                process_video_upload(document_id, temp_path, is_retry=True)
                return
            document.status = "failed"
            document.error_message = f"Video processing failed: {exc}"
            db.commit()

    finally:
        db.close()

    # Clean up temp file only once, after all attempts are done and db is closed.
    if not is_retry and os.path.exists(temp_path):
        os.unlink(temp_path)