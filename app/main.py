from fastapi import FastAPI, HTTPException
from app.services.gmail_service import get_emails_from_last_24_hours, authenticate_gmail
from app.services.summarizer import run_rag_daily, generate_summary_for_emails
from app.services.summarizer import process_emails
from contextlib import asynccontextmanager
from app.services.scheduler import start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    start_scheduler()
    yield
    # Shutdown (cleanup if needed later)

# Initialize FastAPI app
app = FastAPI(
    title="MailSmart API",
    description="AI-powered 24-hour Email Summarizer (Gmail + Gemini)",
    version="1.0.2",
    lifespan=lifespan
)


@app.get("/")
def root():
    return {"message": "Welcome to MailSmart API 🚀"}


@app.get("/raw-emails", summary="Fetch raw emails", description="Returns last 24h Gmail emails (From, Subject, Snippet).")
def raw_emails(limit: int = 10):
    try:
        emails = get_emails_from_last_24_hours(max_results=limit)
        return {"emails": emails}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail fetch failed: {str(e)}")


@app.get("/summarized-emails", summary="Fetch categorized & summarized emails", description="Returns last 24h Gmail emails categorized and summarized by AI")
def summarized_emails(limit: int = 10):
    try:
        emails = get_emails_from_last_24_hours(max_results=limit)
        summarized = process_emails(emails)
        return {"emails": summarized}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Summarization failed: {str(e)}")


@app.get("/test-fetch", summary="Debug: Print emails in server logs")
def test_fetch(limit: int = 10):
    try:
        emails = get_emails_from_last_24_hours(max_results=limit, debug=True)
        print("\n--- MAILSMART 24-HOUR EMAIL CHECK ---\n")
        for e in emails:
            print("📩 From:", e['from'])
            print("📝 Subject:", e['subject'])
            print("🔍 Snippet:", e['snippet'])
            print("-----")
        return {"status": f"✅ Emails printed in backend logs (limit={limit})"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail fetch failed: {str(e)}")


@app.get("/auth", summary="Force Gmail re-login")
def auth():
    try:
        authenticate_gmail(force_refresh=True)
        return {"status": "✅ Gmail authentication successful, token.json refreshed"}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail auth failed: {str(e)}")


from app.services.summarizer import process_emails

@app.get(
    "/summarized-emails",
    summary="Fetch categorized & summarized emails",
    description="Returns last 24h Gmail emails categorized and summarized by AI"
)
def summarized_emails(limit: int = 10):
    try:
        emails = get_emails_from_last_24_hours(max_results=limit)
        summarized = process_emails(emails)
        return {"emails": summarized}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Summarization failed: {str(e)}")

# in app/main.py add:

@app.get("/summarized-emails", summary="Fetch RAG-powered summarized emails")
def summarized_emails(regenerate: bool = False):
    try:
        if regenerate:
            summary = run_rag_daily()
            return {"emails": summary}
        # else read latest log if exists
        import glob, json, os
        files = sorted(glob.glob("logs/summary_*.json"), reverse=True)
        if files:
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"emails": data.get("summary")}
        # fallback to live run
        summary = run_rag_daily()
        return {"emails": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history", summary="Summary run history")
def history(limit:int = 10):
    import glob, json
    files = sorted(glob.glob("logs/summary_*.json"), reverse=True)[:limit]
    out = []
    for fpath in files:
        with open(fpath,"r",encoding="utf-8") as f:
            out.append(json.load(f))
    return {"history": out}
