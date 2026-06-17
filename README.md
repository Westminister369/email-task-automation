# Email Task Automation

Extract unread Gmail messages, summarize them with the OpenAI API, save the results to Google Sheets, and mark processed emails as read.

## What it does

1. Connects to the Gmail API and finds the latest unread inbox emails.
2. Extracts each email's subject, body text, and date.
3. Sends the email content to the OpenAI API for:
   - A concise 3-4 line summary
   - Actionable tasks as bullet points
4. Appends the result to Google Sheets with these columns:
   - Date
   - Email Subject
   - Summary
   - Tasks
5. Marks the email as read after the row is successfully saved.

## Project files

- `email_task_automation.py` - main automation script
- `requirements.txt` - Python dependencies
- `README.md` - setup and usage guide

## Prerequisites

- Python 3.10+
- An OpenAI API key
- A Google Cloud project with Gmail API and Google Sheets API enabled
- OAuth desktop app credentials downloaded as `credentials.json`
- A Google Sheet where the authenticated Google account can edit rows

Google's Python quickstarts use the Google API client libraries and OAuth flow for local testing. The OpenAI Python SDK uses `OPENAI_API_KEY` from the environment unless passed explicitly.

## Google setup

1. Create or open a Google Cloud project.
2. Enable both APIs:
   - Gmail API
   - Google Sheets API
3. Configure the OAuth consent screen.
4. Create OAuth Client ID credentials for a **Desktop app**.
5. Download the OAuth JSON file and save it in this project as `credentials.json`.
6. Create a Google Sheet and add a tab named `Email Tasks`.
7. Add this header row to columns A-D:

   ```text
   Date | Email Subject | Summary | Tasks
   ```

8. Copy the spreadsheet ID from the Sheet URL:

   ```text
   https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit
   ```

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Required:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_SHEET_ID="your-google-spreadsheet-id"
```

Optional:

```bash
export GOOGLE_CREDENTIALS_FILE="credentials.json"
export GOOGLE_TOKEN_FILE="token.json"
export GOOGLE_SHEET_RANGE="Email Tasks!A:D"
export MAX_EMAILS="10"
export GMAIL_QUERY="is:unread in:inbox"
export OPENAI_MODEL="gpt-4.1-mini"
export LOG_LEVEL="INFO"
```

## Usage

Run the automation:

```bash
python email_task_automation.py
```

On the first run, a browser-based Google OAuth flow opens. After authorization, the script writes `token.json` so future runs can refresh credentials automatically.

## Error handling behavior

- Missing environment variables fail fast with clear messages.
- Google API failures are logged and do not mark emails as read.
- OpenAI API failures are logged and do not mark emails as read.
- Emails with no extractable body text are skipped and left unread.
- Emails are marked as read only after successful Sheet append.

## Scaling notes

The script is intentionally modular:

- `fetch_unread_message_ids` controls Gmail search and batching.
- `parse_email` and `extract_body_text` isolate email parsing.
- `analyze_email` isolates OpenAI prompting and response parsing.
- `append_to_sheet` isolates persistence.
- `process_email` handles one message end-to-end.

For production use, consider adding scheduled execution, retries with backoff, structured JSON logging, secret management, and a service-specific deployment model.
