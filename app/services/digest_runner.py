# app/services/digest_runner.py
from app.services.summarizer import run_rag_daily
from app.services.formatter import format_digest
from app.services.emailer import send_email
from app.services.gmail_service import authenticate_gmail

def run_and_email_digest(max_results: int = 20):
    """
    Full daily pipeline: fetch emails, summarize, format digest, send email.
    Always sends the digest back to the authenticated user.
    """
    # 1️⃣ Authenticate Gmail (token.json + scopes)
    service = authenticate_gmail()

    # 2️⃣ Run RAG summarization
    summary = run_rag_daily(max_results=max_results)

    # 3️⃣ Format digest text
    digest_text = format_digest(summary)

    # 4️⃣ Recipient is always self
    user_email = service.users().getProfile(userId="me").execute()["emailAddress"]
    recipients = [user_email]

    # 5️⃣ Send digest
    for recipient in recipients:
        send_email(service, to=recipient, subject="📩 MailSmart Daily Digest", body=digest_text)

    print(f"✅ Digest sent to {len(recipients)} recipient (self).")
    return summary
