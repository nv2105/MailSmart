# app/main.py
import os
import glob
import json
from datetime import datetime
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from contextlib import asynccontextmanager

# services
from app.services.scheduler import start_scheduler
from app.services.vector_store import search_emails
from app.services.digest_runner import run_and_email_digest
from app.services.summarizer import run_rag_daily, summarize_emails_direct
from app.services.gmail_service import get_emails_from_last_24_hours, authenticate_gmail

# --- Templates & Static ---
templates = Jinja2Templates(directory="app/templates")
app = FastAPI(title="MailSmart API", version="1.0.0")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

LOG_DIR = os.getenv("LOG_DIR", "logs")
ESSENTIAL_PATH = "config/essential.json"
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", 7))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", 0))

@asynccontextmanager
async def lifespan(app_: FastAPI):
    # Start scheduler
    try:
        start_scheduler()
    except Exception as e:
        print("⚠️ Scheduler failed to start:", e)
    yield

app.router.lifespan_context = lifespan

# -------------------- Helpers --------------------
def load_summaries():
    summaries = []
    if os.path.exists(LOG_DIR):
        for fname in sorted(os.listdir(LOG_DIR), reverse=True):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(LOG_DIR, fname), "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    continue
                data.setdefault("run_time", fname.replace("summary_", "").replace(".json", ""))
                emails = data.get("summary", {}).get("summary_of_emails", [])
                normalized_emails = [
                    {"summary": e.get("summary", "") if isinstance(e, dict) else e,
                     "sender": e.get("sender", "Unknown") if isinstance(e, dict) else "Unknown"}
                    for e in emails
                ]
                data["total_emails"] = len(emails)
                data["important_emails"] = normalized_emails
                summaries.append(data)
    return summaries

def load_essentials():
    if not os.path.exists(ESSENTIAL_PATH):
        return {"senders": []}
    with open(ESSENTIAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_essentials(data):
    os.makedirs("config", exist_ok=True)
    with open(ESSENTIAL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# -------------------- Routes --------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request, "current_year": datetime.now().year})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    summaries = load_summaries()
    return templates.TemplateResponse("dashboard.html", {"request": request, "summaries": summaries, "current_year": datetime.now().year})

@app.get("/history", response_class=HTMLResponse)
async def history(request: Request):
    history = load_summaries()
    return templates.TemplateResponse("history.html", {"request": request, "history": history, "current_year": datetime.now().year})

@app.get("/essentials", response_class=HTMLResponse)
async def essentials_page(request: Request):
    data = load_essentials()
    return templates.TemplateResponse("essentials.html", {"request": request, "essentials": data.get("senders", []), "current_year": datetime.now().year})

# -------------------- API Endpoints --------------------
@app.post("/run-now")
def run_now():
    try:
        result = run_and_email_digest()
        return JSONResponse({"status": "ok", "summary": result})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/raw-emails")
def raw_emails(limit: int = 10):
    """
    Fetch recent emails (last 24 hours) using Gmail API.
    Works locally or on deployment headlessly.
    """
    try:
        return {"emails": get_emails_from_last_24_hours(max_results=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/summarize")
def summarize_endpoint(regenerate: bool = False, limit: int = 20):
    try:
        if regenerate:
            return {"summary": run_rag_daily(max_results=limit)}
        files = sorted(glob.glob(os.path.join(LOG_DIR, "summary_*.json")), reverse=True)
        if files:
            with open(files[0], "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return {"summary": data.get("summary")}
        return {"summary": run_rag_daily(max_results=limit)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize/direct")
def summarize_direct(payload: dict):
    try:
        emails = payload.get("emails", [])
        return {"summary": summarize_emails_direct(emails)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/search")
def search(q: str, top_k: int = 5):
    try:
        return {"query": q, "results": search_emails(q, top_k=top_k)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ✅ Gmail Auth Endpoints ---
@app.get("/auth")
def auth(interactive: bool = False):
    """
    Gmail authentication endpoint.
    - interactive=False: headless, just uses saved token/env
    - interactive=True: opens OAuth browser to allow user change
    """
    try:
        authenticate_gmail(force_refresh=interactive, interactive=interactive)
        return {"status": "Gmail auth success"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


# Essentials add/remove
@app.post("/api/essentials/add")
def api_add_essential(body: dict = Body(...)):
    sender = body.get("sender")
    if not sender:
        raise HTTPException(status_code=400, detail="Missing sender field")
    data = load_essentials()
    if sender not in data["senders"]:
        data["senders"].append(sender)
        save_essentials(data)
    return {"status": "added", "senders": data["senders"]}

@app.post("/api/essentials/remove")
def api_remove_essential(body: dict = Body(...)):
    sender = body.get("sender")
    if not sender:
        raise HTTPException(status_code=400, detail="Missing sender field")
    data = load_essentials()
    data["senders"] = [s for s in data["senders"] if s != sender]
    save_essentials(data)
    return {"status": "removed", "senders": data["senders"]}
