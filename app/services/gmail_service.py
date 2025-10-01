import os
import base64
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.services.vector_store import upsert_emails

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_emails_from_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials/client_secret.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    results = service.users().messages().list(
        userId='me', q='newer_than:1d', maxResults=10
    ).execute()
    messages = results.get('messages', [])
    email_data = []

    for msg in messages:
        msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_detail['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
        sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
        snippet = msg_detail.get('snippet', '')
        email_data.append({"from": sender, "subject": subject, "snippet": snippet})

    # ✅ Store emails into Qdrant
    if email_data:
        upsert_emails(email_data)

    return email_data
