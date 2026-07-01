import re
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..vector_store import query_chunks, get_chunks_near_timestamp
import os
from dotenv import load_dotenv

load_dotenv()

embeddings_model = GoogleGenerativeAIEmbeddings(
    model="models/gemini-embedding-001",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite",
    google_api_key=os.getenv("GEMINI_API_KEY")
)

SYSTEM_PROMPT = """You are a helpful assistant that answers questions strictly based on the provided document context.

If the question cannot be answered from the context provided, respond with exactly:
"I can only answer questions related to the uploaded document."

Do not use any external knowledge. Only use the context below.

Context:
{context}
"""

def _extract_timestamp_seconds(query: str) -> int | None:
    """Extract a timestamp from the query and return total seconds, or None."""
    match = re.search(r'(\d{1,2}):(\d{2})', query)
    if match:
        return int(match.group(1)) * 60 + int(match.group(2))
    return None


def _retrieve_chunks(query: str, document_id: int) -> list[str]:
    """Vector search + nearest-timestamp match, merged and deduplicated."""
    query_embedding = embeddings_model.embed_query(query)
    vector_chunks = query_chunks(query_embedding, document_id)

    target_secs = _extract_timestamp_seconds(query)
    if target_secs is not None:
        ts_chunks = get_chunks_near_timestamp(document_id, target_secs)
        # Prepend timestamp-matched chunks (most relevant for the query),
        # then append vector results that aren't duplicates.
        seen = set(ts_chunks)
        merged = list(ts_chunks)
        for c in vector_chunks:
            if c not in seen:
                seen.add(c)
                merged.append(c)
        return merged

    return vector_chunks


def get_rag_response(query: str, document_id: int) -> str:
    chunks = _retrieve_chunks(query, document_id)

    if not chunks:
        return "I can only answer questions related to the uploaded document."

    context = "\n\n".join(chunks)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}")
    ])
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"context": context, "question": query})

def stream_rag_response(query: str, document_id: int):
    chunks = _retrieve_chunks(query, document_id)

    if not chunks:
        yield "I can only answer questions related to the uploaded document."
        return

    context = "\n\n".join(chunks)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}")
    ])
    chain = prompt | llm | StrOutputParser()

    for chunk in chain.stream({"context": context, "question": query}):
        yield chunk