@echo off
cd /d %~dp0
py -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist .env copy .env.example .env
echo.
echo Setup complete.
echo 1. Open .env and add OPENAI_API_KEY.
echo 2. For direct publishing, add Pinterest App ID/Secret and run:
echo    python scripts\pinterest_oauth.py
echo 3. Start with run_windows.bat
pause
