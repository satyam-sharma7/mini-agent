import os
import datetime
import base64
from email.message import EmailMessage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

AUTH_CRED_PATH = './data/auth_crediantials/'

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar'
]

def get_authenticated_service(api_name, version):
    creds = None
    if os.path.exists(AUTH_CRED_PATH + 'token.json'):
        creds = Credentials.from_authorized_user_file(AUTH_CRED_PATH + 'token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(AUTH_CRED_PATH + 'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(AUTH_CRED_PATH + 'token.json', 'w') as token:
            token.write(creds.to_json())
    return build(api_name, version, credentials=creds)


gmail_service = get_authenticated_service("gmail", "v1")
calendar_service = get_authenticated_service("calendar", "v3")
