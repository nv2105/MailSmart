# app/services/gmail_service.py
import os
import json
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from fastapi import HTTPException

# Gmail scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

def authenticate_gmail():
    """
    Authenticate Gmail API headlessly using Base64 env variables.
    """
    try:
        # Load token from Base64 env variable
        token_b64 = os.getenv("GOOGLE_TOKEN_JSON_B64")
        if not token_b64:
            raise HTTPException(status_code=500, detail="GOOGLE_TOKEN_JSON_B64 not set in environment")
        token_json = base64.b64decode(token_b64).decode("utf-8")
        token_dict = json.loads(token_json)

        # Load client secret from Base64 env variable
        client_b64 = os.getenv("GOOGLE_CLIENT_SECRET_JSON_B64")
        if not client_b64:
            raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_SECRET_JSON_B64 not set in environment")
        client_json = base64.b64decode(client_b64).decode("utf-8")
        client_dict = json.loads(client_json)

        # Build credentials object
        creds = Credentials.from_authorized_user_info(info=token_dict, scopes=SCOPES)

        # Add client_id and client_secret for refresh
        client_info = client_dict.get("installed", client_dict.get("web", {}))
        creds.client_id = client_info.get("client_id")
        creds.client_secret = client_info.get("client_secret")

        # Build Gmail service
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
