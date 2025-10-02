# app/services/emailer.py
from email.mime.text import MIMEText
import base64

def send_email(service, to: str, subject: str, body: str):
    """
    Send plain text email via Gmail API service.
    Always uses 'me' as the authenticated sender.
    """
    message = MIMEText(body, "plain")
    message["to"] = to
    message["subject"] = subject

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    send_message = {"raw": raw}

    return service.users().messages().send(userId="me", body=send_message).execute()
