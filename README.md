# AI Email Automation Dashboard

A static, GitHub Pages-ready dashboard for controlling an AI Email Automation system. The current UI stores setup values in `localStorage`, simulates the automation run, and preserves timestamped logs locally. A backend worker can be connected later to run the real Gmail → OpenAI → Google Sheets workflow.

## Dashboard features

- Dark, responsive dashboard UI with a header and sidebar navigation.
- Setup sections for:
  - Gmail API credentials placeholder
  - OpenAI API key input
  - Google Sheets ID input
  - Automation run controls
  - Logs / output history
- Save buttons for setup values using browser `localStorage`.
- Simulated automation run with loading spinner and mock output:
  - `Fetched 5 emails`
  - `Summarized successfully`
  - `Tasks saved`
- Timestamped logs that persist in `localStorage`.
- Plain HTML, CSS, and JavaScript with no heavy frontend framework.

## Project structure

```text
index.html
style.css
script.js
email_task_automation.py
requirements.txt
README.md
```

The static dashboard uses:

- `index.html` for the page structure and dashboard sections.
- `style.css` for the dark responsive layout.
- `script.js` for localStorage persistence, simulated runs, and dynamic logs.

The existing Python script can be used as a starting point for a future backend worker.

## Run locally

Open `index.html` directly in your browser, or serve the folder locally:

```bash
python -m http.server 8000
```

Then visit:

```text
http://localhost:8000
```

## Deploy on GitHub Pages

1. Commit and push this repository to GitHub.
2. Open the repository on GitHub.
3. Go to **Settings → Pages**.
4. Under **Build and deployment**, choose:
   - Source: **Deploy from a branch**
   - Branch: your deployment branch, usually `main`
   - Folder: `/ (root)`
5. Click **Save**.
6. GitHub will publish the dashboard at a URL similar to:

   ```text
   https://<your-username>.github.io/<repository-name>/
   ```

Because the dashboard is static and uses only `index.html`, `style.css`, and `script.js`, no build step is required.

## Future backend integration

The dashboard is currently frontend-only. To connect it to the real automation system later:

1. Create a backend endpoint such as `POST /api/run-automation`.
2. Move secret handling to the backend:
   - Store `OPENAI_API_KEY` in server-side environment variables or a secret manager.
   - Store Google OAuth tokens securely server-side.
   - Avoid sending raw API keys or OAuth credentials from the browser in production.
3. Replace the simulated run in `script.js` with a `fetch()` call to your backend endpoint.
4. Have the backend run the Gmail/OpenAI/Sheets workflow and return structured status updates.
5. Stream or poll backend logs and render them in the Logs / Output panel.

Example future frontend call:

```js
const response = await fetch('/api/run-automation', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ sheetId: state.config.sheetId }),
});
const result = await response.json();
```

## Current security note

This dashboard stores values in browser `localStorage` only for local prototyping. Do not store production OpenAI API keys or Google OAuth credentials in client-side storage. Use a backend service with server-side secrets before handling real accounts or sensitive emails.

## Python automation prototype

The repository also includes `email_task_automation.py`, which demonstrates the backend workflow for fetching unread Gmail messages, summarizing them with OpenAI, writing rows to Google Sheets, and marking processed messages as read.

Install Python dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Required environment variables for the Python prototype:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export GOOGLE_SHEET_ID="your-google-spreadsheet-id"
```

Optional environment variables:

```bash
export GOOGLE_CREDENTIALS_FILE="credentials.json"
export GOOGLE_TOKEN_FILE="token.json"
export GOOGLE_SHEET_RANGE="Email Tasks!A:D"
export MAX_EMAILS="10"
export GMAIL_QUERY="is:unread in:inbox"
export OPENAI_MODEL="gpt-4.1-mini"
export LOG_LEVEL="INFO"
```

Run the prototype:

```bash
python email_task_automation.py
```
