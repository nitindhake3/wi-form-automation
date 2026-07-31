import os
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set

from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

from config import AppConfig
from logger import get_logger
from auth import is_auth_valid

logger = get_logger("form_handler")

SCREENSHOTS_DIR = Path("screenshots")

class FormSubmissionError(Exception):
    """Custom exception raised when Google Form submission fails."""
    pass

class FormAuthExpiredError(Exception):
    """Custom exception raised when Google Authentication session has expired."""
    pass

class FormHandler:
    """Automates filling and submitting multi-page Google Forms using Playwright and stored session auth."""

    def __init__(self, config: AppConfig, auth_file: str = "auth.json"):
        self.config = config
        self.auth_file = Path(auth_file)
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    def _random_delay(self, min_sec: float = 0.5, max_sec: float = 1.2) -> None:
        """Applies a random delay to simulate human typing/clicking behavior."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _take_screenshot(self, page: Page, prefix: str = "page") -> str:
        """Captures a screenshot of the current page state."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = SCREENSHOTS_DIR / f"{prefix}_{timestamp}.png"
        try:
            page.screenshot(path=str(filename), full_page=True)
            logger.info(f"Saved screenshot: {filename.resolve()}")
            return str(filename)
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return ""

    def _fill_active_page_fields(self, page: Page, resolved_answers: Dict[str, str]) -> None:
        """Fills all visible inputs, radios, checkboxes, and textareas on the currently active form page."""
        time.sleep(1.0)

        # 1. Fill all visible textareas (Paragraph questions)
        textareas = page.locator("textarea").all()
        for ta in textareas:
            try:
                if ta.is_visible():
                    ta.scroll_into_view_if_needed()
                    self._random_delay(0.3, 0.8)
                    ta.click()
                    ta.fill(".")
                    logger.info("Filled visible textarea with '.'")
            except Exception as e:
                logger.warning(f"Could not fill textarea: {e}")

        # 2. Fill all visible short text inputs
        inputs = page.locator("input[type='text'], input[type='email'], input[type='number']").all()
        for inp in inputs:
            try:
                if inp.is_visible():
                    inp.scroll_into_view_if_needed()
                    self._random_delay(0.3, 0.8)
                    inp.click()
                    inp.fill(".")
                    logger.info("Filled visible text input with '.'")
            except Exception as e:
                logger.warning(f"Could not fill text input: {e}")

        # 3. Match radio buttons for configured answers
        radios = page.locator("div[role='radio']").all()
        for radio in radios:
            try:
                if not radio.is_visible():
                    continue
                radio_text = (radio.get_attribute("aria-label") or radio.inner_text() or "").strip()
                for q_title, answer_val in resolved_answers.items():
                    if str(answer_val).lower() in radio_text.lower() or radio_text.lower() in str(answer_val).lower():
                        radio.scroll_into_view_if_needed()
                        self._random_delay(0.3, 0.8)
                        radio.click()
                        logger.info(f"Selected radio option: '{radio_text}'")
                        break
            except Exception as e:
                logger.warning(f"Could not select radio: {e}")

        # 4. Match checkboxes for configured answers
        checkboxes = page.locator("div[role='checkbox']").all()
        for cb in checkboxes:
            try:
                if not cb.is_visible():
                    continue
                cb_text = (cb.get_attribute("aria-label") or cb.inner_text() or "").strip()
                for q_title, answer_val in resolved_answers.items():
                    if str(answer_val).lower() in cb_text.lower() or "record" in cb_text.lower():
                        cb.scroll_into_view_if_needed()
                        self._random_delay(0.3, 0.8)
                        if cb.get_attribute("aria-checked") != "true":
                            cb.click()
                        logger.info(f"Checked checkbox: '{cb_text}'")
                        break
            except Exception as e:
                logger.warning(f"Could not select checkbox: {e}")

    def submit_form_once(self, headless: bool = True) -> bool:
        """Executes a single attempt to open, fill all pages, and submit the Google Form."""
        if not is_auth_valid(self.auth_file):
            raise FormAuthExpiredError(
                f"Authentication file '{self.auth_file}' is missing or invalid. Please run 'python main.py --setup-auth'."
            )

        resolved_answers = self.config.get_resolved_answers()

        with sync_playwright() as p:
            logger.info(f"Launching Playwright browser (headless={headless}) with saved auth...")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                storage_state=str(self.auth_file),
                viewport={"width": 1280, "height": 900}
            )
            page = context.new_page()

            try:
                logger.info(f"Navigating to Google Form URL: {self.config.form_url}")
                page.goto(self.config.form_url, wait_until="networkidle", timeout=60000)

                if "accounts.google.com" in page.url or "signin" in page.url:
                    self._take_screenshot(page, "auth_expired")
                    raise FormAuthExpiredError(
                        "Google authentication session has EXPIRED! Please run 'python main.py --setup-auth' to re-authenticate."
                    )

                page.wait_for_selector("form, div[role='heading']", timeout=30000)
                logger.info("Google Form loaded successfully.")
                time.sleep(1.5)

                max_pages = 10
                page_count = 0

                while page_count < max_pages:
                    page_count += 1
                    logger.info(f"--- Processing Form Page {page_count} ---")

                    # Fill all visible fields on the current page section
                    self._fill_active_page_fields(page, resolved_answers)
                    time.sleep(1.0)

                    # Find all visible buttons on the page
                    buttons = page.locator("div[role='button'], span.N2T0ea, div.uArLbf").all()
                    submit_btn = None
                    next_btn = None

                    for btn in buttons:
                        try:
                            if not btn.is_visible():
                                continue
                            txt = btn.inner_text().strip().lower()
                            if len(txt) > 20:
                                continue
                            if txt == "submit" or txt == "submit form":
                                submit_btn = btn
                                break
                            elif txt == "next":
                                next_btn = btn
                        except Exception:
                            continue

                    # If Submit button is present and visible, click Submit!
                    if submit_btn:
                        logger.info("Found Submit button! Clicking 'Submit' to complete form...")
                        submit_btn.scroll_into_view_if_needed()
                        self._random_delay(0.8, 1.5)
                        submit_btn.click()

                        # Wait for confirmation screen using Playwright .or_() locator matching
                        logger.info("Waiting for submission confirmation page...")
                        confirmation_locator = (
                            page.locator("text='Your response has been recorded'")
                            .or_(page.locator("text='Submit another response'"))
                            .or_(page.locator("text='response has been recorded'"))
                            .or_(page.locator("text='Thank you for filling'"))
                            .or_(page.locator("div.freebirdFormviewqaFormrecConfirmationMessage"))
                        )

                        confirmation_locator.first.wait_for(timeout=30000)
                        self._take_screenshot(page, "success_confirmation")

                        logger.info("SUCCESS: Google Form submitted successfully!")
                        return True

                    # Otherwise, if Next button is present, click Next!
                    if next_btn:
                        logger.info("Clicking 'Next' button to proceed to the next section...")
                        next_btn.scroll_into_view_if_needed()
                        self._random_delay(0.8, 1.5)
                        next_btn.click()
                        time.sleep(2.0)
                        page.wait_for_load_state("networkidle")
                        continue

                    # If neither Submit nor Next button is found
                    logger.warning("Neither Submit nor Next button is visible on this page.")
                    self._take_screenshot(page, f"no_buttons_page_{page_count}")
                    break

                raise FormSubmissionError("Completed page loop without finding confirmation page or submit button.")

            except PlaywrightTimeoutError as te:
                logger.error(f"Timeout occurred during form automation: {te}")
                self._take_screenshot(page, "timeout_error")
                raise FormSubmissionError(f"Form submission timed out: {te}")
            except (FormSubmissionError, FormAuthExpiredError):
                raise
            except Exception as e:
                logger.error(f"Unexpected error during form submission: {e}")
                self._take_screenshot(page, "unexpected_error")
                raise FormSubmissionError(f"Unexpected error: {e}")
            finally:
                browser.close()

    def submit_form_with_retry(self, max_retries: int = 3, headless: bool = True) -> bool:
        """Attempts form submission up to max_retries times with delays between retries."""
        for attempt in range(1, max_retries + 1):
            logger.info(f"=== Starting Form Submission Attempt {attempt} of {max_retries} ===")
            try:
                success = self.submit_form_once(headless=headless)
                if success:
                    logger.info(f"Submission succeeded on attempt {attempt}.")
                    return True
            except FormAuthExpiredError as ae:
                logger.error(f"CRITICAL AUTH ERROR: {ae}")
                print(f"\n[CRITICAL ERROR] {ae}\n")
                return False
            except FormSubmissionError as se:
                logger.warning(f"Attempt {attempt} failed: {se}")
                if attempt < max_retries:
                    retry_delay = 5 * attempt
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"All {max_retries} submission attempts failed.")

        return False
