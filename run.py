from app.services.gmail_service import get_emails_from_last_24_hours

emails = get_emails_from_last_24_hours()
for e in emails:
    print("📩 From:", e['from'])
    print("📝 Subject:", e['subject'])
    print("🔍 Snippet:", e['snippet'])
    print("-----")