from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from ..vector_store import query_chunks
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

def get_rag_response(query: str, document_id: int) -> str:
    query_embedding = embeddings_model.embed_query(query)
    chunks = query_chunks(query_embedding, document_id)

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
    query_embedding = embeddings_model.embed_query(query)
    chunks = query_chunks(query_embedding, document_id)

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