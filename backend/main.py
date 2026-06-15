from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Document Chatbot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "AI Document Chatbot API is running"}