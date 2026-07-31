# Google Form Auto-Fill Bot 🤖

A production-ready Python automation tool powered by **Playwright** and **APScheduler** to automatically fill and submit authenticated Google Forms daily.

Designed specifically for Google Forms requiring Google account authentication (e.g. `@kalvium.community`), avoiding repetitive manual logins by using Playwright's persistent browser storage state (`auth.json`).

---

## 📁 Project Structure

```
attendance-bot/
├── main.py              # CLI entry point (--setup-auth, --run-now, default scheduler)
├── auth.py              # Manual Google login launcher & session state validator
├── form_handler.py      # Resilient Google Form Playwright automation engine
├── scheduler.py         # APScheduler wrapper for daily execution
├── config.py            # Configuration loader and validator
├── logger.py            # Logging setup (console + logs/attendance_bot.log)
├── config.json          # Configuration file (URL, submit_time, timezone, answers)
├── auth.json            # Saved Playwright authenticated browser state (cookies)
├── requirements.txt     # Python package dependencies
├── README.md            # Comprehensive user guide and documentation
├── logs/                # Automated execution log files
└── screenshots/         # Automated failure/error screenshot captures
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites

- Python 3.12+ installed
- Active `@kalvium.community` Google Account (or relevant institutional account)

### 2. Installation

Clone or open the project folder in your terminal and install dependencies:

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install required Python packages
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

---

### 3. One-Time Authentication Setup (`auth.json`)

Google Forms restricted to specific domain accounts cannot be accessed anonymously. To authenticate:

1. Run the one-time authentication script:
   ```bash
   python main.py --setup-auth
   ```
2. A browser window will open. Log into your `@kalvium.community` account manually (including 2FA if required).
3. Once logged in and redirected to Google Home or your form, return to your terminal and press **ENTER**.
4. The authenticated session state is saved to `auth.json`. Playwright will reuse this file for background execution.

---

### 4. Configuration (`config.json`)

Edit `config.json` to specify your Google Form URL, submission time, timezone, and answers:

```json
{
  "form_url": "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform",
  "submit_time": "08:00",
  "timezone": "Asia/Kolkata",
  "answers": {
    "Full Name": "John Doe",
    "Email Address": "john.doe@kalvium.community",
    "Department": "Computer Science",
    "Status": "Present",
    "Date": "{{DATE}}",
    "Comments": "Daily submission complete."
  }
}
```

#### Dynamic Answer Placeholders
You can use dynamic placeholders in answer values:
- `{{DATE}}` or `{{TODAY}}` -> Formatted as `YYYY-MM-DD` (e.g. `2026-07-31`)
- `{{TIME}}` -> Formatted as `HH:MM` (e.g. `08:00`)
- `{{DATETIME}}` -> Formatted as `YYYY-MM-DD HH:MM`

---

## 🏃 Running the Bot

### Test Immediate Submission (`--run-now`)
Test your configuration and form filler immediately without waiting for the scheduler:

```bash
python main.py --run-now
```

### Start Daily Scheduler (Default)
To run the bot as a background service that triggers every day at `submit_time`:

```bash
python main.py
```

Leave the process running. It will wake up every day at the designated time, open the form with your stored authentication, fill the answers, submit the form, and log the status.

---

## 🛡️ Error Handling & Troubleshooting

| Issue | Solution / Cause |
|---|---|
| **Google Authentication Session Expired** | Google periodic security cookie refresh invalidates old sessions. Run `python main.py --setup-auth` to log in again and update `auth.json`. |
| **Field Not Found / Form Changed** | Ensure question names in `config.json` match the labels on the Google Form. Screenshots of failures are saved automatically in `screenshots/`. |
| **Timezone Warning** | Verify the `"timezone"` string in `config.json` matches a valid IANA timezone (e.g., `Asia/Kolkata`, `America/New_York`, `UTC`). |
| **Network Timeout** | The bot automatically retries up to 3 times with exponential backoff on transient network glitches. |

---

## ☁️ Setting Up Cloud Automation with GitHub Actions (100% Serverless)

With **GitHub Actions**, the bot runs on GitHub's cloud servers every **Monday–Friday at 11:00 AM IST**. Your laptop can be completely turned off!

### Step 1: Push Code to your GitHub Repository
```bash
git init
git add .
git commit -m "Add Google Form Auto-Fill Bot with GitHub Actions"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### Step 2: Get your `auth.json` Content
Run the helper script in your terminal to view your login secret:
```bash
python print_secret.py
```
Copy the full JSON text output.

### Step 3: Add `AUTH_JSON` Secret on GitHub
1. Go to your repository on **GitHub.com**.
2. Click **Settings** ➔ **Secrets and variables** ➔ **Actions**.
3. Click **New repository secret**.
4. Set **Name**: `AUTH_JSON`
5. Set **Secret**: Paste the copied JSON text.
6. Click **Add secret**.

### Step 4: Test Manual Run on GitHub
1. Go to the **Actions** tab on your GitHub repository.
2. Click **Daily Google Form Auto-Fill Bot**.
3. Click **Run workflow** ➔ **Run workflow**.

GitHub will launch a cloud runner, install Playwright, authenticate using your secret, fill the form, and log success!

