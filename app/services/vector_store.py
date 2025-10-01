import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
EMB_MODEL = os.getenv("EMB_MODEL", "all-MiniLM-L6-v2")

# Init clients
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embedder = SentenceTransformer(EMB_MODEL)

COLLECTION_NAME = "emails"

def ensure_collection():
    """Ensure emails collection exists"""
    from qdrant_client.http import models
    qdrant.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
    )

def upsert_emails(emails: list):
    """Store emails in Qdrant"""
    vectors = embedder.encode([e['subject'] + " " + e['snippet'] for e in emails])
    payloads = [
        {"from": e['from'], "subject": e['subject'], "snippet": e['snippet']}
        for e in emails
    ]
    qdrant.upsert(
        collection_name=COLLECTION_NAME,
        points=[
            {"id": i, "vector": vec.tolist(), "payload": payload}
            for i, (vec, payload) in enumerate(zip(vectors, payloads))
        ]
    )

def search_emails(query: str, top_k: int = 5):
    """Retrieve most relevant emails using semantic search"""
    vector = embedder.encode([query])[0]
    results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector.tolist(),
        limit=top_k
    )
    return [hit.payload for hit in results]
