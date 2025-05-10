@echo off
TITLE PFA Launcher

ECHO Setting environment for Real Data Mode (expenses_dev.db)...
set PFA_FORCE_DB=expenses_dev.db

ECHO Activating conda environment 'genai'...
REM Use 'call' to ensure environment variables persist
call conda activate genai

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate conda environment 'genai'. Make sure conda is configured for batch scripts.
    pause
    goto :eof
)

ECHO Changing directory to script location (Project Root)...
cd /d "%~dp0"
ECHO Current Directory: %CD%


ECHO Starting FastAPI backend server (Uvicorn)...
REM MODIFIED: Use --app-dir to specify the location of the 'app' module
REM The path provided to --app-dir is relative to the current directory (%CD%, which is the project root)
start "PFA Backend Server" cmd /k uvicorn app.server:app --app-dir assistant/finance-assistant --host 0.0.0.0 --port 8000

ECHO Waiting a few seconds for server to initialize...
timeout /t 5 /nobreak > nul


ECHO Starting Streamlit frontend application...
REM Use start to launch in a new window. cmd /k keeps window open.
start "PFA Streamlit Frontend" cmd /k streamlit run streamlit/main.py


:eof
ECHO Launcher script finished. Backend and Frontend should be running in separate windows.