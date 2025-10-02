# app/main.py
import os
import glob
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi import Body


# import services
from app.services.digest_runner import run_and_email_digest
from app.services.gmail_service import get_emails_from_last_24_hours, authenticate_gmail
from app.services.summarizer import run_rag_daily, summarize_emails_direct
from app.services.vector_store import search_emails
from app.services.scheduler import start_scheduler

# templates directory
templates = Jinja2Templates(directory="app/templates")

ESSENTIAL_PATH = "config/essential.json"

# lifespan to start scheduler (modern FastAPI pattern)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # start scheduler in background (safe to call; it will return quickly)
    try:
        start_scheduler()
    except Exception as e:
        print("⚠️ Scheduler failed to start:", e)
    yield
    # no special shutdown actions for now

app = FastAPI(
    title="MailSmart API",
    description="AI-powered 24-hour Email Summarizer (Gmail + Groq + Gemini fallback)",
    version="1.0.0",
    lifespan=lifespan
)

# root
@app.get("/")
def root():
    return {"message": "Welcome to MailSmart API 🚀"}

# raw emails endpoint
@app.get("/raw-emails", summary="Fetch raw emails", description="Returns last 24h Gmail emails (From, Subject, Snippet).")
def raw_emails(limit: int = 10):
    try:
        emails = get_emails_from_last_24_hours(max_results=limit)
        return {"emails": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail fetch failed: {str(e)}")

# RAG / Summarize endpoint (regenerate forces a live run)
@app.get("/summarize", summary="Fetch RAG-powered summarized emails")
def summarize_endpoint(regenerate: bool = False, limit: int = 20):
    try:
        if regenerate:
            # run full RAG pipeline: fetch -> index -> summarize -> save
            summary = run_rag_daily(max_results=limit)
            return {"summary": summary}
        # else read latest log file if present
        files = sorted(glob.glob("logs/summary_*.json"), reverse=True)
        if files:
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"summary": data.get("summary")}
        # fallback to live run
        summary = run_rag_daily(max_results=limit)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# direct summarize (send emails list in request body if needed)
@app.post("/summarize/direct", summary="Summarize given emails payload")
def summarize_direct(payload: dict):
    try:
        # payload expected: {"emails": [ {from, subject, snippet}, ... ]}
        emails = payload.get("emails", [])
        summary = summarize_emails_direct(emails)
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# search in Qdrant semantic store
@app.get("/search", summary="Semantic search over indexed emails")
def search(q: str, top_k: int = 5):
    try:
        hits = search_emails(q, top_k=top_k)
        return {"query": q, "results": hits}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# auth endpoint to force Gmail re-login
@app.get("/auth", summary="Force Gmail re-login")
def auth():
    try:
        authenticate_gmail(force_refresh=True)
        return {"status": "✅ Gmail authentication successful, token.json refreshed"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail auth failed: {str(e)}")

# history dashboard (simple)
@app.get("/history", response_class=HTMLResponse, summary="Summary run history")
def history(request: Request, limit: int = 20):
    files = sorted(glob.glob("logs/summary_*.json"), reverse=True)[:limit]
    data = []
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data.append(json.load(f))
        except Exception:
            continue
    return templates.TemplateResponse("history.html", {"request": request, "summaries": data})

# manual run-now endpoint for UI button (POST)
@app.post("/run-now", summary="Manual trigger to fetch+summarize and send digest")
def run_now():
    """
    Manual trigger to fetch emails, summarize, format digest,
    and send digest email to all senders.
    """
    try:
        summary = run_and_email_digest()
        return JSONResponse({"status": "ok", "summary": summary})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




def load_essentials():
    if not os.path.exists(ESSENTIAL_PATH):
        return {"senders": []}
    with open(ESSENTIAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_essentials(data):
    os.makedirs("config", exist_ok=True)
    with open(ESSENTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

@app.get("/essentials", summary="Get list of essential senders")
def get_essentials():
    return load_essentials()

@app.post("/essentials/add", summary="Add a new essential sender")
def add_essential(sender: str = Body(..., embed=True)):
    data = load_essentials()
    if sender not in data["senders"]:
        data["senders"].append(sender)
        save_essentials(data)
    return {"status": "added", "senders": data["senders"]}

@app.post("/essentials/remove", summary="Remove an essential sender")
def remove_essential(sender: str = Body(..., embed=True)):
    data = load_essentials()
    data["senders"] = [s for s in data["senders"] if s != sender]
    save_essentials(data)
    return {"status": "removed", "senders": data["senders"]}