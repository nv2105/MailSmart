from fastapi import FastAPI, HTTPException
from app.services.gmail_service import get_emails_from_last_24_hours, authenticate_gmail
from app.services.summarize import process_emails

# Initialize FastAPI app
app = FastAPI(
    title="MailSmart API",
    description="AI-powered 24-hour Email Summarizer (Gmail + Gemini)",
    version="1.0.2"
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
