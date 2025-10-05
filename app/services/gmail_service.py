# app/services/gmail_service.py
import os
import json
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from fastapi import HTTPException

# Gmail scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

# Local paths (for local dev / presentation)
LOCAL_CLIENT_PATH = "credentials/client_secret.json"
LOCAL_TOKEN_PATH = "token.json"


def authenticate_gmail(force_refresh: bool = False, interactive: bool = False):
    """
    Authenticate Gmail API:
    - Local JSON files take priority (for local testing / presentation)
    - Falls back to Base64 env variables (for headless deployment)
    - If interactive=True, opens browser OAuth to change account
    """
    try:
        creds = None

        # 1️⃣ Try local token first
        if os.path.exists(LOCAL_TOKEN_PATH) and not force_refresh:
            creds = Credentials.from_authorized_user_file(LOCAL_TOKEN_PATH, SCOPES)

        # 2️⃣ If no local token, try Base64 env
        else:
            token_b64 = os.getenv("GOOGLE_TOKEN_JSON_B64")
            client_b64 = os.getenv("GOOGLE_CLIENT_SECRET_JSON_B64")
            if not token_b64 or not client_b64:
                raise HTTPException(
                    status_code=500,
                    detail="No local token or Base64 env variables found for Gmail auth"
                )

            token_json = base64.b64decode(token_b64).decode("utf-8")
            token_dict = json.loads(token_json)

            creds = Credentials.from_authorized_user_info(info=token_dict, scopes=SCOPES)

        # 3️⃣ If interactive requested or force_refresh, run OAuth flow
        if interactive or force_refresh or not creds.valid:
            # Load client secret for OAuth
            if os.path.exists(LOCAL_CLIENT_PATH):
                with open(LOCAL_CLIENT_PATH, "r", encoding="utf-8") as f:
                    client_dict = json.load(f)
            else:
                client_json = base64.b64decode(os.getenv("GOOGLE_CLIENT_SECRET_JSON_B64")).decode("utf-8")
                client_dict = json.loads(client_json)

            flow = InstalledAppFlow.from_client_config(client_dict, SCOPES)
            creds = flow.run_local_server(port=0)  # <-- opens browser

            # Save token for future use
            with open(LOCAL_TOKEN_PATH, "w", encoding="utf-8") as f:
                f.write(creds.to_json())

        # 4️⃣ Refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())

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
