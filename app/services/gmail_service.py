import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

#Define the Gmail permission scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
# Handles OAuth and returns authorized Gmail API service
    creds = None
# Check if login already saved
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        # First-time login: opens browser for Gmail auth
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials/client_secret.json', SCOPES)
        creds = flow.run_local_server(port=0)

        # Save the credentials for future use
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Build the Gmail API service
    service = build('gmail', 'v1', credentials=creds)
    return service
def test_auth():
    service = authenticate_gmail()
    print("✅ Gmail authentication successful!")

def get_emails_from_last_24_hours():
# Fetches emails from the last 24 hours
    service = authenticate_gmail()
    # Gmail query to filter messages newer than 1 day
    query = 'newer_than:1d'

    # Fetch up to 10 recent messages
    results = service.users().messages().list(userId='me', q=query, maxResults=10).execute()
    messages = results.get('messages', [])

    email_data = []

    for msg in messages:
        # Fetch full message detail
        msg_detail = service.users().messages().get(userId='me', id=msg['id']).execute()

        # Extract headers
        headers = msg_detail['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        snippet = msg_detail.get('snippet', '')

        # Save the details
        email_data.append({
            'from': sender,
            'subject': subject,
            'snippet': snippet
        })

    return email_data
