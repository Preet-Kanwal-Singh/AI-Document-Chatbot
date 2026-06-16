from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from ..vector_store import store_chunks
import os
import time
from dotenv import load_dotenv

load_dotenv()

embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

def chunk_and_embed(text: str, document_id: int):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(text)

    BATCH_SIZE = 50
    all_embeddings = []

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        batch_embeddings = embeddings_model.embed_documents(batch)
        all_embeddings.extend(batch_embeddings)
        if i + BATCH_SIZE < len(chunks):
            time.sleep(65)

    store_chunks(chunks, all_embeddings, document_id)
    return len(chunks)