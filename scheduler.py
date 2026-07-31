import time
import pytz
from datetime import datetime, date
from pathlib import Path
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import AppConfig
from form_handler import FormHandler
from logger import get_logger

logger = get_logger("scheduler")

LAST_SUBMITTED_FILE = Path("logs") / "last_submitted_date.txt"

class FormScheduler:
    """Manages scheduling and recurring execution of the Google Form auto-fill bot with catch-up logic."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.form_handler = FormHandler(config)
        self.scheduler = BlockingScheduler(timezone=pytz.timezone(config.timezone_str))
        LAST_SUBMITTED_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _mark_today_submitted(self, tz_str: str) -> None:
        """Records today's date in last_submitted_date.txt to prevent duplicate submissions."""
        today_str = datetime.now(pytz.timezone(tz_str)).strftime("%Y-%m-%d")
        try:
            with open(LAST_SUBMITTED_FILE, "w", encoding="utf-8") as f:
                f.write(today_str)
            logger.info(f"Recorded submission date '{today_str}' in {LAST_SUBMITTED_FILE}.")
        except Exception as e:
            logger.error(f"Failed to record submission date: {e}")

    def _is_today_already_submitted(self, tz_str: str) -> bool:
        """Checks if the form was already submitted today."""
        if not LAST_SUBMITTED_FILE.exists():
            return False
        today_str = datetime.now(pytz.timezone(tz_str)).strftime("%Y-%m-%d")
        try:
            with open(LAST_SUBMITTED_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
            return content == today_str
        except Exception:
            return False

    def _check_and_run_missed_job(self) -> None:
        """Checks if laptop booted after the scheduled time on a weekday and executes catch-up submission if missed."""
        tz = pytz.timezone(self.config.timezone_str)
        now = datetime.now(tz)
        hour, minute = map(int, self.config.submit_time.split(":"))

        # 0 = Monday ... 4 = Friday, 5 = Saturday, 6 = Sunday
        is_weekday = now.weekday() < 5
        is_past_submit_time = (now.hour > hour) or (now.hour == hour and now.minute >= minute)

        if is_weekday and is_past_submit_time:
            if not self._is_today_already_submitted(self.config.timezone_str):
                logger.info(
                    f"[CATCH-UP] Laptop was powered off at {self.config.submit_time}. "
                    f"Executing missed daily form submission now..."
                )
                success = self.form_handler.submit_form_with_retry(max_retries=3)
                if success:
                    self._mark_today_submitted(self.config.timezone_str)
                    logger.info("[CATCH-UP] Missed form submission completed SUCCESSFULLY.")
                else:
                    logger.error("[CATCH-UP] Missed form submission attempt FAILED.")
            else:
                logger.info("Form has already been submitted for today.")

    def _scheduled_job(self) -> None:
        """The daily scheduled job function executed by APScheduler."""
        logger.info(f"Triggering scheduled daily Google Form submission job at {datetime.now()}...")
        try:
            success = self.form_handler.submit_form_with_retry(max_retries=3)
            if success:
                self._mark_today_submitted(self.config.timezone_str)
                logger.info("Scheduled form submission completed SUCCESSFULLY.")
            else:
                logger.error("Scheduled form submission FAILED.")
        except Exception as e:
            logger.error(f"Uncaught exception in scheduled job: {e}")

    def start(self) -> None:
        """Parses submit_time, checks for missed jobs, and starts the APScheduler blocking loop."""
        # 1. Run catch-up check immediately on startup
        self._check_and_run_missed_job()

        # 2. Configure recurring daily schedule
        hour, minute = map(int, self.config.submit_time.split(":"))
        trigger = CronTrigger(
            day_of_week=self.config.days_of_week,
            hour=hour,
            minute=minute,
            timezone=pytz.timezone(self.config.timezone_str)
        )

        self.scheduler.add_job(
            self._scheduled_job,
            trigger=trigger,
            id="daily_google_form_job",
            name="Daily Google Form Submission (Mon-Fri)",
            replace_existing=True
        )

        logger.info("======================================================")
        logger.info(f"Scheduler STARTED. Form will be submitted {self.config.days_of_week.upper()} at {self.config.submit_time} ({self.config.timezone_str}).")
        logger.info("Press Ctrl+C to exit scheduler.")
        logger.info("======================================================")

        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped by user.")
            self.scheduler.shutdown()
