@echo off
cd /d %~dp0
py -m venv .venv
call .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-local.txt
if not exist .env copy .env.example .env
echo.
echo Setup complete.
echo 1. For local Studio/Publisher, add AMAZON_TRACKING_ID to .env.
echo    OPENAI_API_KEY is NOT required for Template + Local renderer.
echo 2. For legacy direct publishing, add Pinterest App ID/Secret and run:
echo    python scripts\pinterest_oauth.py
echo 3. Start Studio: run_studio_windows.bat
echo 4. Start Publisher: run_publisher_windows.bat
echo 5. Legacy one-click app: run_windows.bat
pause
