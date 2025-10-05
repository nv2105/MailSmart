# app/services/gmail_service.py
import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from fastapi import HTTPException

# Gmail scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# Token path for refresh token storage
TOKEN_PATH = os.getenv("GMAIL_TOKEN", "token.json")

def authenticate_gmail(force_refresh: bool = False):
    """
    Authenticate with Gmail API.
    For Render deployment, load client_secret from environment variable.
    """
    creds = None

    # Load token if it exists and no force_refresh
    if os.path.exists(TOKEN_PATH) and not force_refresh:
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    else:
        # Get credentials JSON from environment variable
        client_secret_json = os.getenv("GMAIL_CLIENT_SECRET_JSON")
        if not client_secret_json:
            raise HTTPException(status_code=500, detail="GMAIL_CLIENT_SECRET_JSON not set in environment")

        creds_dict = json.loads(client_secret_json)

        # Run OAuth flow
        flow = InstalledAppFlow.from_client_config(creds_dict, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        return service
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail authentication failed: {str(e)}")


def get_emails_from_last_24_hours(max_results: int = 20, debug: bool = False):
    """
    Fetch emails from the last 24 hours using Gmail API.
    """
    service = authenticate_gmail()
    query = "newer_than:1d in:all"
    try:
        results = service.users().messages().list(userId="me", q=query, maxResults=max_results).execute()
        messages = results.get("messages", [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail API list error: {e}")

    email_data = []
    for m in messages:
        try:
            msg_detail = service.users().messages().get(userId="me", id=m["id"]).execute()
            headers = msg_detail.get("payload", {}).get("headers", [])
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
            sender = next((h["value"] for h in headers if h["name"] == "From"), "Unknown Sender")
            snippet = msg_detail.get("snippet", "")
            email_data.append({"from": sender, "subject": subject, "snippet": snippet, "id": m["id"]})
        except Exception:
            continue

    if debug:
        print(f"Fetched {len(email_data)} emails from Gmail")
    return email_data
