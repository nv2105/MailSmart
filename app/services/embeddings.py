# app/services/embeddings.py
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

# Load embedding model from .env
EMB_MODEL = os.getenv("EMB_MODEL", "all-MiniLM-L6-v2")
_model = SentenceTransformer(EMB_MODEL)

def get_embedding(text: str) -> list:
    """
    Generate embeddings using SentenceTransformer model.
    """
    return _model.encode(text).tolist()

def email_to_embedding(email: dict) -> list:
    """
    Converts an email dict into an embedding vector.
    """
    text = f"From: {email['from']}\nSubject: {email['subject']}\nSnippet: {email['snippet']}"
    return get_embedding(text)
