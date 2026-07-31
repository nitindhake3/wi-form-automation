import argparse
import sys
from pathlib import Path

from config import AppConfig, ConfigValidationError
from auth import setup_auth, is_auth_valid
from form_handler import FormHandler
from scheduler import FormScheduler
from logger import get_logger, setup_logger

logger = setup_logger("main")

def main():
    parser = argparse.ArgumentParser(
        description="Google Form Auto-Fill Bot with Playwright & APScheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --setup-auth     # Open browser to log in and create auth.json
  python main.py --run-now        # Test submit the form immediately
  python main.py                  # Start daily scheduler daemon
        """
    )

    parser.add_argument(
        "--setup-auth",
        action="store_true",
        help="Launch interactive browser to log into Google Account (@kalvium.community) and save session to auth.json"
    )

    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Submit the form immediately once for testing, skipping the scheduler"
    )

    parser.add_argument(
        "--config",
        default="config.json",
        help="Path to configuration file (default: config.json)"
    )

    args = parser.parse_args()

    # Mode 1: Interactive Authentication Setup
    if args.setup_auth:
        try:
            cfg = AppConfig(args.config)
            target = cfg.form_url if cfg.form_url.startswith("http") else "https://accounts.google.com"
        except Exception:
            target = "https://accounts.google.com"

        success = setup_auth(target_url=target)
        sys.exit(0 if success else 1)

    # Load and validate configuration
    try:
        config = AppConfig(args.config)
    except ConfigValidationError as e:
        logger.error(f"Configuration error: {e}")
        print(f"\n[ERROR] Configuration error: {e}\n")
        sys.exit(1)

    # Check authentication session presence
    if not is_auth_valid():
        logger.error("Authentication file 'auth.json' is missing or invalid.")
        print("\n" + "=" * 70)
        print("[WARNING] Authentication session not found!")
        print("Please run the one-time authentication setup first:")
        print("    python main.py --setup-auth")
        print("=" * 70 + "\n")
        sys.exit(1)

    # Mode 2: Immediate Execution (--run-now)
    if args.run_now:
        logger.info("Executing immediate form submission (--run-now)...")
        handler = FormHandler(config)
        success = handler.submit_form_with_retry(max_retries=3)
        if success:
            logger.info("Immediate form submission completed successfully!")
            sys.exit(0)
        else:
            logger.error("Immediate form submission failed.")
            sys.exit(1)

    # Mode 3: Default Daily Scheduler Mode
    logger.info("Starting Google Form Auto-Fill Scheduler...")
    scheduler = FormScheduler(config)
    scheduler.start()

if __name__ == "__main__":
    main()
