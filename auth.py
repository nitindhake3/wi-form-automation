import os
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

from logger import get_logger

logger = get_logger("auth")

AUTH_FILE = Path("auth.json")
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

CHROMIUM_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-infobars",
    "--start-maximized",
    "--window-size=1280,900",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-first-run",
    "--no-service-autorun",
    "--password-store=basic",
]

STEALTH_INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    window.chrome = { runtime: {} };
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""

def is_auth_valid(auth_path: Path = AUTH_FILE) -> bool:
    """Checks whether the auth.json file exists and contains stored cookies/origins."""
    if not auth_path.exists():
        logger.warning(f"Auth file '{auth_path}' does not exist.")
        return False

    try:
        with open(auth_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cookies = data.get("cookies", [])
        origins = data.get("origins", [])

        if not cookies and not origins:
            logger.warning(f"Auth file '{auth_path}' contains no cookies or origins.")
            return False

        logger.info(f"Auth file '{auth_path}' is present with {len(cookies)} cookies.")
        return True
    except Exception as e:
        logger.error(f"Failed to read auth file '{auth_path}': {e}")
        return False

def setup_auth(auth_path: Path = AUTH_FILE, target_url: str = "https://accounts.google.com") -> bool:
    """
    Launches a headful browser for the user to log into their Google account.
    Saves the browser storage state to auth.json upon user confirmation.
    """
    logger.info("=== Starting One-Time Google Authentication Setup ===")
    logger.info("A browser window will open. Please log into your Google Account.")

    with sync_playwright() as p:
        # Launch interactive headful browser with stealth settings
        browser = p.chromium.launch(
            headless=False,
            args=CHROMIUM_ARGS
        )
        context_kwargs = {
            "user_agent": DEFAULT_USER_AGENT,
            "viewport": {"width": 1280, "height": 800},
            "locale": "en-US",
            "timezone_id": "Asia/Kolkata",
            "extra_http_headers": {
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "accept-language": "en-US,en;q=0.9"
            }
        }
        if auth_path.exists():
            context_kwargs["storage_state"] = str(auth_path)

        context = browser.new_context(**context_kwargs)
        context.add_init_script(STEALTH_INIT_SCRIPT)
        page = context.new_page()

        page.goto(target_url, wait_until="networkidle")

        print("\n" + "=" * 70)
        print("ACTION REQUIRED: Log into your Google Account in the opened browser window.")
        print("The script will automatically detect when login is complete, or you can press ENTER here.")
        print("=" * 70 + "\n")

        try:
            import msvcrt
            has_msvcrt = True
        except ImportError:
            has_msvcrt = False

        login_detected = False
        target_account_email = "nitin.dhake.s73@kalvium.community"
        account_clicked = False
        password_entered = False
        try:
            for _ in range(300): # Wait up to 5 minutes
                try:
                    curr_url = page.url
                    if "docs.google.com/forms" in curr_url and "accounts.google.com" not in curr_url and "signin" not in curr_url:
                        logger.info("Auto-detected successful login to Google Form!")
                        login_detected = True
                        break
                except Exception:
                    pass

                # Auto-click target account if on Account Chooser screen (only once)
                if not account_clicked:
                    try:
                        account_btn = page.locator(
                            f"div[role='link'][data-identifier='{target_account_email}'], "
                            f"div[data-identifier='{target_account_email}'], "
                            f"div[data-email='{target_account_email}']"
                        ).first
                        if account_btn.is_visible():
                            logger.info(f"Auto-clicking account '{target_account_email}' on Account Chooser...")
                            account_btn.click()
                            account_clicked = True
                    except Exception:
                        pass

                # If password input is visible and password is in env, fill it automatically
                password = (os.environ.get("AUTH_PASSWORD") or os.environ.get("PASSWORD") or os.environ.get("GOOGLE_PASSWORD") or "").strip()
                if password and not password_entered:
                    try:
                        pwd_inp = page.locator("input[type='password'], input[name='Passwd'], input[name='password']").first
                        if pwd_inp.is_visible():
                            logger.info("Auto-filling password from environment...")
                            pwd_inp.fill(password)
                            time.sleep(0.5)
                            pwd_inp.press("Enter")
                            password_entered = True
                    except Exception:
                        pass

                if has_msvcrt and msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b'\r', b'\n'):
                        logger.info("User confirmed login by pressing ENTER.")
                        break

                time.sleep(1)
        except KeyboardInterrupt:
            logger.warning("Authentication setup cancelled by user.")
            browser.close()
            return False

        # Navigate to target form URL if available to ensure docs.google.com cookies are generated
        if target_url and "docs.google.com" in target_url:
            try:
                logger.info("Navigating to Google Form to capture form-specific session state...")
                page.goto(target_url, wait_until="networkidle", timeout=30000)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Could not load form URL during auth setup: {e}")

        # Save storage state
        context.storage_state(path=str(auth_path))
        browser.close()

    if is_auth_valid(auth_path):
        logger.info(f"SUCCESS: Authentication session saved to '{auth_path}'.")
        print(f"\nAuthentication session successfully saved to '{auth_path}'.")
        print("You can now run the scheduler or submit forms automatically!\n")
        return True
    else:
        logger.error(f"FAILURE: Authentication file '{auth_path}' was not saved correctly.")
        return False

if __name__ == "__main__":
    setup_auth()

