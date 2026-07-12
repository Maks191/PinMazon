@echo off
cd /d %~dp0
if not exist .venv (
  echo Virtual environment not found. Run setup_windows.bat first.
  pause
  exit /b 1
)
call .venv\Scripts\activate
streamlit run streamlit_app.py
