# app/services/embeddings.py
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()
EMB_MODEL = os.getenv("EMB_MODEL", "all-MiniLM-L6-v2")

# load model once
_model = SentenceTransformer(EMB_MODEL)

def get_embedding(text: str):
    # returns list[float]
    vec = _model.encode(text, show_progress_bar=False)
    return vec.tolist()

def email_to_embedding(email: dict):
    # convert email dict to single text then embedding
    text = f"From: {email.get('from','')}\nSubject: {email.get('subject','')}\nSnippet: {email.get('snippet','')}"
    return get_embedding(text)