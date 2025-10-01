# app/services/scheduler.py
import os
import json
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from app.services.gmail_service import get_emails_from_gmail
from app.services.vector_store import upsert_emails
from app.services.summarizer import summarize_emails

LOG_FILE = "logs/summaries.json"

def daily_job():
    """
    Fetch emails, insert into Qdrant, summarize, and save to logs.
    """
    print("⏰ Running daily job...")

    # 1. Fetch emails
    emails = get_emails_from_gmail()
    if not emails:
        print("⚠️ No new emails in last 24h")
        return

    # 2. Store in Qdrant
    upsert_emails(emails)

    # 3. Summarize
    summary = summarize_emails(emails)

    # 4. Save summary to logs
    os.makedirs("logs", exist_ok=True)
    log_entry = {"time": datetime.now().isoformat(), "summary": summary}
    
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    else:
        data = []

    data.append(log_entry)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print("✅ Daily summary generated and logged.")


def start_scheduler():
    """
    Starts the APScheduler in background for daily job at 7AM.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_job, "cron", hour=7, minute=0)
    scheduler.start()
    print("🚀 Scheduler started (runs daily at 7:00 AM)")
