import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

from logger import get_logger

logger = get_logger("auth")

AUTH_FILE = Path("auth.json")

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
    Launches a headful browser for the user to log into their @kalvium.community Google account.
    Saves the browser storage state to auth.json upon user confirmation.
    """
    logger.info("=== Starting One-Time Google Authentication Setup ===")
    logger.info("A browser window will open. Please log into your @kalvium.community Google Account.")

    with sync_playwright() as p:
        # Launch interactive headful browser
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        page.goto(target_url)

        print("\n" + "=" * 70)
        print("ACTION REQUIRED: Log into your Google Account in the opened browser window.")
        print("Once you are logged in successfully and can see your Form or Google Dashboard,")
        print("return here and press ENTER to save your session state.")
        print("=" * 70 + "\n")

        try:
            input("Press ENTER when login is complete...")
        except KeyboardInterrupt:
            logger.warning("Authentication setup cancelled by user.")
            browser.close()
            return False

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
