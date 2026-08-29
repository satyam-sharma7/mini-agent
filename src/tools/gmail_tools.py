from email.message import EmailMessage
import base64
from langchain_core.tools import tool
from typing import Annotated, Optional

from src.tools.google_auth import gmail_service


@tool
def read_mail(
    n: Annotated[Optional[int], "Number of recent mails to read."] = 5
) -> list:
    """Read the most recent n messages from the inbox."""
    if n is None or n <= 0:
        return []

    results = (
        gmail_service.users().messages()
        .list(userId="me", labelIds=["INBOX"], maxResults=n)
        .execute()
    )
    messages = results.get("messages", [])
    inbox = []
    for message in messages:
        msg = gmail_service.users().messages().get(userId="me", id=message["id"]).execute()
        inbox.append({"id": message["id"], "snippet": msg["snippet"]})
    return inbox


@tool
def send_mail(
    to: Annotated[str, "Recipient's email address (e.g. user@domain.com)"], 
    subject: Annotated[str, "Subject line, kept concise"], 
    body: Annotated[str, "Plain text email body"]
):
    """Sends an email via the Gmail API. Use this when the user asks to email someone."""
    message = EmailMessage()
    message.set_content(body)
    message['to'] = to
    message['subject'] = subject
    
    # Gmail API requires base64 encoding
    encoded_message = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
    return gmail_service.users().messages().send(userId="me", body=encoded_message).execute()
        

def search_mail():
    pass




# OPENAI Function Schema

# read_mail_schema = {
#     "type": "function",
#     "function":{
#         "name": "read_mail",
#         "description": "Read the most recent n messages from the inbox.",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "n": {
#                     "type": "integer",
#                     "description": "The number of recent messages to retrieve. Defaults to 5 if omitted.",
#                 }
#             }
#         }
#     }
# }


# send_mail_schema = {
#     "type": "function",
#     "function":{
#         "name": "send_mail",
#         "description": "Send a mail",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "to": {
#                     "type": "string",
#                     "description": "The mail address of recipient whom message is to be sent.",
#                 },
#                 "subject": {
#                     "type": "string",
#                     "description": "The topic of the Mail. Should be intresting so recipient's don't ignore the mail.",
#                 },
#                 "body": {
#                     "type": "string",
#                     "description": "The message that you want to send.",
#                 }
#             },
#             "required": ["to", "subject", "body"],
#         }
#     }
# }
