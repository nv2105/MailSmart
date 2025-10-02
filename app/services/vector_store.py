# app/services/vector_store.py
import os
import uuid
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.services.embeddings import get_embedding

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "mailsmart_emails")


# init client
def _get_client():
    if QDRANT_API_KEY:
        return QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    return QdrantClient(url=QDRANT_URL)


def ensure_collection():
    client = _get_client()
    try:
        client.get_collection(COLLECTION_NAME)
    except Exception:
        # create with vector size 384 for all-MiniLM-L6-v2
        client.recreate_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
        )


def upsert_emails(emails: list):
    """Insert or update emails into Qdrant with deterministic UUIDs"""
    client = _get_client()
    ensure_collection()
    points = []
    for idx, e in enumerate(emails):
        doc_text = f"{e.get('from','')}\n{e.get('subject','')}\n{e.get('snippet','')}"
        vec = get_embedding(doc_text)
        payload = {
            "from": e.get("from"),
            "subject": e.get("subject"),
            "snippet": e.get("snippet")
        }
        # ✅ Convert Gmail ID (string) → deterministic UUID
        raw_id = str(e.get("id", idx))
        safe_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, raw_id))
        points.append(models.PointStruct(id=safe_id, vector=vec, payload=payload))
    client.upsert(collection_name=COLLECTION_NAME, points=points)


def search_emails(query: str, top_k: int = 5):
    client = _get_client()
    ensure_collection()
    q_vec = get_embedding(query)
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=q_vec,
        limit=top_k,
        with_payload=True
    )
    out = []
    for r in results:
        out.append({"id": r.id, "score": r.score, "payload": r.payload})
    return out