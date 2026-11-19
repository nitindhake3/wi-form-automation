import base64
import json
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

AUTH_FILE = Path("auth.json")
CONFIG_FILE = Path("config.json")

def verify_session_valid() -> bool:
    print("[1/4] Verifying authentication session against Google Form...")
    if not AUTH_FILE.exists():
        print("[ERROR] auth.json does not exist. Please run 'python main.py --setup-auth' first.")
        return False

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    form_url = cfg["form_url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=str(AUTH_FILE))
        page = context.new_page()
        try:
            page.goto(form_url, wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)
            url = page.url
            if "accounts.google.com" in url or "signin" in url:
                print(f"[ERROR] Session is not logged in! Redirected to: {url}")
                browser.close()
                return False
            print(f"[SUCCESS] Session is valid! Successfully loaded: {url}")
            browser.close()
            return True
        except Exception as e:
            print(f"[ERROR] Verification failed: {e}")
            browser.close()
            return False

def sync_secret_to_github() -> bool:
    print("[2/4] Base64 encoding auth.json and syncing to GitHub Secrets...")
    with open(AUTH_FILE, "rb") as f:
        raw_bytes = f.read()

    b64_secret = base64.b64encode(raw_bytes).decode("utf-8")
    
    # Set AUTH_JSON secret
    proc = subprocess.run(
        ["gh", "secret", "set", "AUTH_JSON", "--body", b64_secret],
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        print(f"[ERROR] Failed to set AUTH_JSON secret: {proc.stderr}")
        return False
    print("[SUCCESS] Secret 'AUTH_JSON' updated on GitHub repository.")

    # Ensure GOOGLE_EMAIL secret is also set
    subprocess.run(
        ["gh", "secret", "set", "GOOGLE_EMAIL", "--body", "nitin.dhake.s73@kalvium.community"],
        capture_output=True,
        text=True
    )
    return True

def trigger_and_watch_workflow() -> bool:
    print("[3/4] Triggering GitHub Actions workflow 'daily_form.yml'...")
    proc = subprocess.run(
        ["gh", "workflow", "run", "daily_form.yml"],
        capture_output=True,
        text=True
    )
    if proc.returncode != 0:
        print(f"[ERROR] Failed to trigger workflow: {proc.stderr}")
        return False
    print("[SUCCESS] Workflow triggered successfully!")

    print("[4/4] Monitoring workflow run on GitHub...")
    time.sleep(5)

    # Get the latest run ID
    run_proc = subprocess.run(
        ["gh", "run", "list", "--workflow=daily_form.yml", "--limit=1", "--json=databaseId,status,conclusion"],
        capture_output=True,
        text=True
    )
    if run_proc.returncode != 0 or not run_proc.stdout.strip():
        print("[WARNING] Could not fetch run ID immediately, waiting...")
        time.sleep(5)
        run_proc = subprocess.run(
            ["gh", "run", "list", "--workflow=daily_form.yml", "--limit=1", "--json=databaseId,status,conclusion"],
            capture_output=True,
            text=True
        )

    runs = json.loads(run_proc.stdout)
    if not runs:
        print("[ERROR] No runs found.")
        return False

    run_id = str(runs[0]["databaseId"])
    print(f"Monitoring GitHub Actions Run ID: {run_id}")
    print(f"Watch live at: https://github.com/nitindhake3/wi-form-automation/actions/runs/{run_id}")

    # Watch run until completion
    watch_proc = subprocess.run(["gh", "run", "watch", run_id, "--exit-status"])
    if watch_proc.returncode == 0:
        print(f"\n[SUCCESS] GitHub Actions Workflow Run {run_id} COMPLETED SUCCESSFULLY! Checkmark: PASS\n")
        return True
    else:
        print(f"\n[FAILURE] Workflow run {run_id} failed. Checking logs...")
        subprocess.run(["gh", "run", "view", run_id, "--log-failed"])
        return False

if __name__ == "__main__":
    if not verify_session_valid():
        print("\nPlease run:")
        print("    python main.py --setup-auth")
        print("in your terminal to log into your Google Account, then re-run this script.\n")
        sys.exit(1)

    if not sync_secret_to_github():
        sys.exit(1)

    if not trigger_and_watch_workflow():
        sys.exit(1)
