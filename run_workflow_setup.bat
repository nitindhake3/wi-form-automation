@echo off
echo ======================================================================
echo STEP 1: Log into your Google Account in the browser window
echo ======================================================================
python main.py --setup-auth
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Authentication was not completed. Please try again.
    pause
    exit /b 1
)

echo.
echo ======================================================================
echo STEP 2: Syncing Session to GitHub Secrets and Triggering Workflow
echo ======================================================================
python sync_and_run.py
pause
