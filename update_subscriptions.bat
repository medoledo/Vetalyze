@echo off
REM Windows Task Scheduler script to update subscription statuses daily at 12:01 AM
REM 
REM To set up in Windows Task Scheduler:
REM 1. Open Task Scheduler
REM 2. Create Basic Task
REM 3. Name: "Vetalyze Subscription Update"
REM 4. Trigger: Daily at 12:01 AM
REM 5. Action: Start a program
REM 6. Program/script: Path to this batch file
REM 7. Start in: c:\Users\medol\OneDrive\Desktop\vetalyze\backend

cd /d c:\Users\medol\OneDrive\Desktop\vetalyze\backend

REM Activate virtual environment if you're using one
REM call venv\Scripts\activate.bat

REM Run the management command
python manage.py update_subscription_statuses >> logs\subscription_update.log 2>&1

REM Log completion
echo Subscription update completed at %date% %time% >> logs\subscription_update.log
