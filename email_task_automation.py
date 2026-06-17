"""Process unread Gmail messages into summarized task rows in Google Sheets.

This module fetches unread Gmail messages, extracts readable text, asks the
OpenAI API for a short summary and actionable tasks, appends the result to a
Google Sheet, and marks messages as read only after successful processing.
"""

from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, Iterable

from bs4 import BeautifulSoup
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError
from openai import APIError, OpenAI, OpenAIError, RateLimitError

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/spreadsheets",
]
DEFAULT_SHEET_RANGE = "Email Tasks!A:D"
DEFAULT_UNREAD_QUERY = "is:unread in:inbox"


@dataclass(frozen=True)
class AppConfig:
    """Runtime configuration loaded from environment variables."""

    openai_api_key: str
    spreadsheet_id: str
    credentials_file: str = "credentials.json"
    token_file: str = "token.json"
    sheet_range: str = DEFAULT_SHEET_RANGE
    max_emails: int = 10
    gmail_query: str = DEFAULT_UNREAD_QUERY
    openai_model: str = "gpt-4.1-mini"

    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        openai_api_key = require_env("OPENAI_API_KEY")
        spreadsheet_id = require_env("GOOGLE_SHEET_ID")
        return cls(
            openai_api_key=openai_api_key,
            spreadsheet_id=spreadsheet_id,
            credentials_file=os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json"),
            token_file=os.getenv("GOOGLE_TOKEN_FILE", "token.json"),
            sheet_range=os.getenv("GOOGLE_SHEET_RANGE", DEFAULT_SHEET_RANGE),
            max_emails=int(os.getenv("MAX_EMAILS", "10")),
            gmail_query=os.getenv("GMAIL_QUERY", DEFAULT_UNREAD_QUERY),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        )


@dataclass(frozen=True)
class EmailMessage:
    """Simplified email data used by the automation pipeline."""

    message_id: str
    subject: str
    body: str
    date: str


@dataclass(frozen=True)
class EmailAnalysis:
    """Structured OpenAI output for one email."""

    summary: str
    tasks: list[str]


def require_env(name: str) -> str:
    """Return a required environment variable or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def setup_logging() -> None:
    """Configure readable console logging."""
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(message)s",
    )


def authenticate_google(credentials_file: str, token_file: str) -> Credentials:
    """Authenticate with Google APIs using OAuth credentials and token cache."""
    creds: Credentials | None = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(credentials_file):
                raise FileNotFoundError(
                    f"Google OAuth client file not found: {credentials_file}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return creds


def build_services(creds: Credentials) -> tuple[Resource, Resource]:
    """Build Gmail and Sheets API clients."""
    return build("gmail", "v1", credentials=creds), build(
        "sheets", "v4", credentials=creds
    )


def fetch_unread_message_ids(
    gmail_service: Resource, query: str, max_results: int
) -> list[str]:
    """Fetch Gmail message IDs matching the unread query."""
    response = (
        gmail_service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    return [message["id"] for message in response.get("messages", [])]


def get_message(gmail_service: Resource, message_id: str) -> dict[str, Any]:
    """Retrieve a Gmail message payload."""
    return (
        gmail_service.users()
        .messages()
        .get(userId="me", id=message_id, format="full")
        .execute()
    )


def parse_email(message: dict[str, Any]) -> EmailMessage:
    """Extract subject, body, and date from a Gmail API message."""
    payload = message.get("payload", {})
    headers = {
        h.get("name", "").lower(): h.get("value", "")
        for h in payload.get("headers", [])
    }
    subject = headers.get("subject", "(No subject)")
    date = format_email_date(headers.get("date"))
    body = extract_body_text(payload).strip()

    return EmailMessage(
        message_id=message["id"],
        subject=subject,
        body=body,
        date=date,
    )


def format_email_date(raw_date: str | None) -> str:
    """Convert an email date header to an ISO date string."""
    if not raw_date:
        return datetime.now(timezone.utc).date().isoformat()
    try:
        return parsedate_to_datetime(raw_date).date().isoformat()
    except (TypeError, ValueError, IndexError, OverflowError):
        logging.warning("Could not parse email date %r; using current UTC date", raw_date)
        return datetime.now(timezone.utc).date().isoformat()


def extract_body_text(payload: dict[str, Any]) -> str:
    """Extract plain text from a message payload, falling back to HTML text."""
    plain_parts: list[str] = []
    html_parts: list[str] = []

    for part in walk_payload_parts(payload):
        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")
        if not data:
            continue
        decoded = decode_base64url(data)
        if mime_type == "text/plain":
            plain_parts.append(decoded)
        elif mime_type == "text/html":
            html_parts.append(
                BeautifulSoup(decoded, "html.parser").get_text(" ", strip=True)
            )

    if plain_parts:
        return "\n".join(plain_parts)
    return "\n".join(html_parts)


def walk_payload_parts(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    """Yield payload and nested MIME parts recursively."""
    yield payload
    for part in payload.get("parts", []) or []:
        yield from walk_payload_parts(part)


def decode_base64url(data: str) -> str:
    """Decode Gmail's base64url message body text."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8")).decode(
        "utf-8", errors="replace"
    )


def analyze_email(client: OpenAI, model: str, email: EmailMessage) -> EmailAnalysis:
    """Ask OpenAI to summarize an email and extract actionable tasks."""
    if not email.body:
        raise ValueError(f"Email {email.message_id} has no extractable body text")

    prompt = f"""
Analyze this email and return JSON only with keys "summary" and "tasks".
- summary: 3-4 concise lines, joined with newline characters.
- tasks: array of actionable task strings; use an empty array if none.

Subject: {email.subject}
Body:
{email.body[:12000]}
""".strip()

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2,
        text={"format": {"type": "json_object"}},
    )
    content = response.output_text
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI returned invalid JSON: {content[:200]}") from exc

    summary = str(parsed.get("summary", "")).strip()
    tasks = parsed.get("tasks", [])
    if isinstance(tasks, str):
        tasks = [tasks]
    if not summary:
        raise ValueError("OpenAI response did not include a summary")
    cleaned_tasks = [str(task).strip() for task in tasks if str(task).strip()]
    return EmailAnalysis(summary=summary, tasks=cleaned_tasks)


def append_to_sheet(
    sheets_service: Resource,
    spreadsheet_id: str,
    sheet_range: str,
    email: EmailMessage,
    analysis: EmailAnalysis,
) -> None:
    """Append an analyzed email row to Google Sheets."""
    values = [
        [
            email.date,
            email.subject,
            analysis.summary,
            "\n".join(f"• {task}" for task in analysis.tasks),
        ]
    ]
    (
        sheets_service.spreadsheets()
        .values()
        .append(
            spreadsheetId=spreadsheet_id,
            range=sheet_range,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": values},
        )
        .execute()
    )


def mark_as_read(gmail_service: Resource, message_id: str) -> None:
    """Remove the UNREAD label after successful processing."""
    (
        gmail_service.users()
        .messages()
        .modify(userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]})
        .execute()
    )


def process_email(
    gmail_service: Resource,
    sheets_service: Resource,
    openai_client: OpenAI,
    config: AppConfig,
    message_id: str,
) -> None:
    """Process one message end-to-end with isolated error handling."""
    try:
        email = parse_email(get_message(gmail_service, message_id))
        logging.info("Processing email %s: %s", message_id, email.subject)
        analysis = analyze_email(openai_client, config.openai_model, email)
        append_to_sheet(
            sheets_service,
            config.spreadsheet_id,
            config.sheet_range,
            email,
            analysis,
        )
        mark_as_read(gmail_service, message_id)
        logging.info("Processed and marked as read: %s", message_id)
    except (HttpError, GoogleAuthError) as exc:
        logging.exception("Google API failure for message %s: %s", message_id, exc)
    except (RateLimitError, APIError, OpenAIError) as exc:
        logging.exception("OpenAI API failure for message %s: %s", message_id, exc)
    except (ValueError, KeyError, RuntimeError) as exc:
        logging.exception(
            "Skipping message %s due to processing error: %s", message_id, exc
        )


def main() -> None:
    """Run the unread-email processing workflow."""
    setup_logging()
    config = AppConfig.from_env()
    creds = authenticate_google(config.credentials_file, config.token_file)
    gmail_service, sheets_service = build_services(creds)
    openai_client = OpenAI(api_key=config.openai_api_key)

    try:
        message_ids = fetch_unread_message_ids(
            gmail_service, config.gmail_query, config.max_emails
        )
    except HttpError as exc:
        logging.exception("Failed to fetch unread emails: %s", exc)
        return

    if not message_ids:
        logging.info("No unread emails found for query: %s", config.gmail_query)
        return

    logging.info("Found %d unread email(s)", len(message_ids))
    for message_id in message_ids:
        process_email(gmail_service, sheets_service, openai_client, config, message_id)


if __name__ == "__main__":
    main()
