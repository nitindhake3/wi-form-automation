import os
import random
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Set

from playwright.sync_api import sync_playwright, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError

from config import AppConfig
from logger import get_logger
from auth import is_auth_valid, DEFAULT_USER_AGENT, CHROMIUM_ARGS, STEALTH_INIT_SCRIPT

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

    def _extract_target_email(self) -> str:
        """Extracts target email from env vars or config answers."""
        env_email = os.environ.get("GOOGLE_EMAIL") or os.environ.get("EMAIL")
        if env_email:
            return env_email.strip()

        # Check config answers for an email address pattern
        for val in self.config.answers.values():
            if isinstance(val, str):
                match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", val)
                if match:
                    return match.group(0)
        return ""

    def _handle_google_reauth(self, page: Page, context: BrowserContext) -> bool:
        """
        Attempts to handle Google Account Chooser, email entry, and password challenge.
        Refreshes and saves auth.json if authentication succeeds.
        """
        target_email = self._extract_target_email()
        password = (
            os.environ.get("GOOGLE_PASSWORD")
            or os.environ.get("AUTH_PASSWORD")
            or os.environ.get("PASSWORD")
            or ""
        ).strip()

        logger.info(f"Attempting automated Google re-authentication for account '{target_email or 'Unknown'}'...")

        for attempt in range(6):
            url = page.url
            if "docs.google.com/forms" in url and "accounts.google.com" not in url:
                logger.info("Re-authentication successful! Back on Google Form URL.")
                try:
                    context.storage_state(path=str(self.auth_file))
                    logger.info(f"Updated authentication state saved to '{self.auth_file}'.")
                except Exception as e:
                    logger.warning(f"Could not update storage state: {e}")
                return True

            if "accounts.google.com" not in url and "signin" not in url:
                break

            # 1. Check Account Chooser screen FIRST (Account selection)
            account_btn = None
            if target_email:
                btn_match = page.locator(
                    f"div[data-identifier='{target_email}'], "
                    f"div:has-text('{target_email}'), "
                    f"li:has-text('{target_email}'), "
                    f"div[data-email='{target_email}']"
                )
                if btn_match.count() > 0 and btn_match.last.is_visible():
                    account_btn = btn_match.last

            if not account_btn:
                fallback_match = page.locator("div[data-identifier], div.wL32ec, div.Jh9pfc")
                if fallback_match.count() > 0 and fallback_match.first.is_visible():
                    account_btn = fallback_match.first

            if account_btn and account_btn.is_visible():
                logger.info("Found account item on Account Chooser screen. Clicking account...")
                try:
                    account_btn.click()
                    time.sleep(3)
                    page.wait_for_load_state("domcontentloaded")
                    continue
                except Exception as e:
                    logger.warning(f"Failed to click account item: {e}")

            # 2. Check Password Field
            pwd_inp = page.locator("input[type='password'], input[name='Passwd'], input[name='password']")
            if pwd_inp.count() > 0 and pwd_inp.first.is_visible():
                if not password:
                    logger.warning(
                        "Password challenge prompt reached, but 'GOOGLE_PASSWORD' secret is not provided in environment."
                    )
                    break
                logger.info("Entering password and submitting login challenge...")
                pwd_inp.first.fill(password)
                time.sleep(0.5)
                pwd_inp.first.press("Enter")

                next_btn = page.locator("#passwordNext, button:has-text('Next'), div[role='button']:has-text('Next')")
                if next_btn.count() > 0 and next_btn.first.is_visible():
                    try:
                        next_btn.first.click()
                    except Exception:
                        pass

                time.sleep(5)
                page.wait_for_load_state("domcontentloaded")
                continue

            # 3. Check Email Field
            email_inp = page.locator("input[type='email'], input[name='identifier']")
            if email_inp.count() > 0 and email_inp.first.is_visible():
                if not target_email:
                    logger.error("Email prompt reached but no email found in config or environment secrets.")
                    break
                logger.info(f"Entering email '{target_email}'...")
                email_inp.first.fill(target_email)
                time.sleep(0.5)
                email_inp.first.press("Enter")

                next_btn = page.locator("#identifierNext, button:has-text('Next'), div[role='button']:has-text('Next')")
                if next_btn.count() > 0 and next_btn.first.is_visible():
                    try:
                        next_btn.first.click()
                    except Exception:
                        pass

                time.sleep(3)
                page.wait_for_load_state("domcontentloaded")
                continue

            time.sleep(2)

        return "docs.google.com/forms" in page.url and "accounts.google.com" not in page.url

    def _fill_active_page_fields(self, page: Page, resolved_answers: Dict[str, str]) -> None:
        """Fills all visible inputs, radios, checkboxes, and textareas on the currently active form page."""
        time.sleep(1.0)

        # Process each question block container on the page
        question_blocks = page.locator("div[role='listitem'], div.geStF, div.QrBrvd").all()

        if question_blocks:
            for block in question_blocks:
                try:
                    if not block.is_visible():
                        continue

                    # Extract question text from heading inside block
                    heading_el = block.locator("div[role='heading'], span.M7V2ed, div.hoP2b").first
                    q_text = heading_el.inner_text().strip() if heading_el.count() > 0 else ""

                    # Check for textareas (paragraph text)
                    textareas = block.locator("textarea").all()
                    for ta in textareas:
                        if ta.is_visible():
                            ta.scroll_into_view_if_needed()
                            val_to_fill = "."
                            for ans_q, ans_val in resolved_answers.items():
                                if ans_q.lower() in q_text.lower() or q_text.lower() in ans_q.lower():
                                    val_to_fill = str(ans_val)
                                    break
                            ta.click()
                            ta.fill(val_to_fill)
                            logger.info(f"Filled textarea with '{val_to_fill}'")

                    # Check for short text inputs
                    inputs = block.locator("input[type='text'], input[type='email'], input[type='number']").all()
                    for inp in inputs:
                        if inp.is_visible():
                            inp.scroll_into_view_if_needed()
                            val_to_fill = "."
                            for ans_q, ans_val in resolved_answers.items():
                                if ans_q.lower() in q_text.lower() or q_text.lower() in ans_q.lower():
                                    val_to_fill = str(ans_val)
                                    break
                            inp.click()
                            inp.fill(val_to_fill)
                            logger.info(f"Filled text input with '{val_to_fill}'")

                    # Check radios
                    radios = block.locator("div[role='radio']").all()
                    for radio in radios:
                        if not radio.is_visible():
                            continue
                        radio_text = (radio.get_attribute("aria-label") or radio.inner_text() or "").strip()
                        for q_title, answer_val in resolved_answers.items():
                            if str(answer_val).lower() in radio_text.lower() or radio_text.lower() in str(answer_val).lower():
                                radio.scroll_into_view_if_needed()
                                self._random_delay(0.2, 0.5)
                                radio.click()
                                logger.info(f"Selected radio option: '{radio_text}'")
                                break

                    # Check checkboxes
                    checkboxes = block.locator("div[role='checkbox']").all()
                    for cb in checkboxes:
                        if not cb.is_visible():
                            continue
                        cb_text = (cb.get_attribute("aria-label") or cb.inner_text() or "").strip()
                        for q_title, answer_val in resolved_answers.items():
                            if str(answer_val).lower() in cb_text.lower() or "record" in cb_text.lower():
                                cb.scroll_into_view_if_needed()
                                self._random_delay(0.2, 0.5)
                                if cb.get_attribute("aria-checked") != "true":
                                    cb.click()
                                logger.info(f"Checked checkbox: '{cb_text}'")
                                break

                except Exception as e:
                    logger.warning(f"Error processing question block: {e}")

        # Fallback global filling for any unhandled visible inputs
        textareas = page.locator("textarea").all()
        for ta in textareas:
            try:
                if ta.is_visible() and not ta.input_value():
                    ta.scroll_into_view_if_needed()
                    self._random_delay(0.2, 0.5)
                    ta.click()
                    ta.fill(".")
                    logger.info("Filled visible textarea with '.'")
            except Exception:
                pass

        inputs = page.locator("input[type='text'], input[type='email'], input[type='number']").all()
        for inp in inputs:
            try:
                if inp.is_visible() and not inp.input_value():
                    inp.scroll_into_view_if_needed()
                    self._random_delay(0.2, 0.5)
                    inp.click()
                    inp.fill(".")
                    logger.info("Filled visible text input with '.'")
            except Exception:
                pass

        radios = page.locator("div[role='radio']").all()
        for radio in radios:
            try:
                if not radio.is_visible():
                    continue
                radio_text = (radio.get_attribute("aria-label") or radio.inner_text() or "").strip()
                for q_title, answer_val in resolved_answers.items():
                    if str(answer_val).lower() in radio_text.lower() or radio_text.lower() in str(answer_val).lower():
                        radio.scroll_into_view_if_needed()
                        self._random_delay(0.2, 0.5)
                        radio.click()
                        logger.info(f"Selected radio option: '{radio_text}'")
                        break
            except Exception:
                pass

        checkboxes = page.locator("div[role='checkbox']").all()
        for cb in checkboxes:
            try:
                if not cb.is_visible():
                    continue
                cb_text = (cb.get_attribute("aria-label") or cb.inner_text() or "").strip()
                for q_title, answer_val in resolved_answers.items():
                    if str(answer_val).lower() in cb_text.lower() or "record" in cb_text.lower():
                        cb.scroll_into_view_if_needed()
                        self._random_delay(0.2, 0.5)
                        if cb.get_attribute("aria-checked") != "true":
                            cb.click()
                        logger.info(f"Checked checkbox: '{cb_text}'")
                        break
            except Exception:
                pass

    def submit_form_once(self, headless: bool = True) -> bool:
        """Executes a single attempt to open, fill all pages, and submit the Google Form."""
        if not is_auth_valid(self.auth_file):
            raise FormAuthExpiredError(
                f"Authentication file '{self.auth_file}' is missing or invalid. Please run 'python main.py --setup-auth'."
            )

        resolved_answers = self.config.get_resolved_answers()

        with sync_playwright() as p:
            logger.info(f"Launching Playwright browser (headless={headless}) with saved auth & stealth settings...")
            browser = p.chromium.launch(
                headless=headless,
                args=CHROMIUM_ARGS
            )
            context = browser.new_context(
                storage_state=str(self.auth_file),
                user_agent=DEFAULT_USER_AGENT,
                viewport={"width": 1280, "height": 900},
                locale="en-US",
                timezone_id="Asia/Kolkata",
                extra_http_headers={
                    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "accept-language": "en-US,en;q=0.9"
                }
            )
            context.add_init_script(STEALTH_INIT_SCRIPT)
            page = context.new_page()

            try:
                logger.info(f"Navigating to Google Form URL: {self.config.form_url}")
                page.goto(self.config.form_url, wait_until="networkidle", timeout=60000)

                if "accounts.google.com" in page.url or "signin" in page.url:
                    logger.info("Redirected to Google sign-in / account chooser. Attempting automated re-authentication...")
                    reauth_success = self._handle_google_reauth(page, context)
                    if not reauth_success:
                        self._take_screenshot(page, "auth_expired")
                        raise FormAuthExpiredError(
                            "Google authentication session has EXPIRED!\n"
                            "SOLUTIONS:\n"
                            "1. Set 'GOOGLE_PASSWORD' in your GitHub Repository Secrets to allow automated background re-login.\n"
                            "2. Or re-run 'python main.py --setup-auth' on your laptop and update your 'AUTH_JSON' secret."
                        )

                page.wait_for_selector("form, div[role='heading'], div.freebirdFormviewqaFormrecConfirmationMessage", timeout=30000)
                logger.info("Google Form loaded successfully.")
                time.sleep(1.5)

                # Check if form was already submitted today
                already_submitted = (
                    page.locator("text='You\'ve already responded'")
                    .or_(page.locator("text='already responded'"))
                    .or_(page.locator("text='Your response has been recorded'"))
                )
                if already_submitted.first.is_visible():
                    logger.info("SUCCESS: Form has already been submitted!")
                    return True

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
                            .or_(page.locator("text='You\'ve already responded'"))
                            .or_(page.locator("text='already responded'"))
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

