import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from fastapi import HTTPException

load_dotenv()  # Load environment variables from .env

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
TOKEN_PATH = os.getenv("GMAIL_TOKEN", "token.json")
CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS", "credentials/client_secret.json")


def authenticate_gmail(force_refresh: bool = False):
    creds = None
    try:
        if os.path.exists(TOKEN_PATH) and not force_refresh:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())

        service = build('gmail', 'v1', credentials=creds)
        return service

    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Gmail authentication failed: {str(e)}")


def get_emails_from_last_24_hours(max_results: int = None, debug: bool = False):
    max_results = max_results or int(os.getenv("MAX_EMAIL_FETCH", 10))
    service = authenticate_gmail()
    query = 'newer_than:1d'

    results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
    messages = results.get('messages', [])

    email_data = []
    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_detail['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = msg_detail.get('snippet', '')

        email_data.append({'from': sender, 'subject': subject, 'snippet': snippet})

    if debug:
        print(f"Fetched {len(email_data)} emails from Gmail")

    return email_data
