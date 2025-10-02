# app/services/gmail_service.py
import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from fastapi import HTTPException

load_dotenv()

# Gmail scope readonly
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",  # still needed for reading
    "https://www.googleapis.com/auth/gmail.send"       # needed for sending emails
]
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS", "credentials/client_secret.json")
TOKEN_PATH = os.getenv("GMAIL_TOKEN", "token.json")

def authenticate_gmail(force_refresh: bool = False):
    # Handles OAuth and returns authorized Gmail API service
    creds = None
    try:
        if os.path.exists(TOKEN_PATH) and not force_refresh:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, "w", encoding="utf-8") as token:
                token.write(creds.to_json())
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail authentication failed: {str(e)}")

def get_emails_from_last_24_hours(max_results: int = 20, debug: bool = False):
    # Fetches emails from the last 24 hours
    service = authenticate_gmail()
    query = 'newer_than:1d'
    try:
        results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
        messages = results.get('messages', [])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gmail API list error: {e}")

    email_data = []
    for m in messages:
        try:
            msg_detail = service.users().messages().get(userId='me', id=m['id']).execute()
            headers = msg_detail.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
            snippet = msg_detail.get('snippet', '')
            email_data.append({'from': sender, 'subject': subject, 'snippet': snippet, 'id': m['id']})
        except Exception:
            continue

    if debug:
        print(f"Fetched {len(email_data)} emails from Gmail")
    return email_data