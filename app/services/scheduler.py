# app/services/scheduler.py
import os
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from app.services.summarizer import run_rag_daily

from app.services.digest_runner import run_and_email_digest

load_dotenv()
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR", 7))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE", 0))

_scheduler = None



def _job_wrapper():
    try:
        print("⏰ Running scheduled MailSmart job...")
        run_and_email_digest()
        print("✅ Digest email sent successfully.")
    except Exception as e:
        print("⚠️ Scheduled job error:", e)


def start_scheduler():
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    # daily at configured hour:minute
    _scheduler.add_job(_job_wrapper, "cron", hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE)
    _scheduler.start()
    print(f"🚀 Scheduler started - daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} (Asia/Kolkata)")