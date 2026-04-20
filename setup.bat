@echo off
REM ─────────────────────────────────────────────
REM  FaceTrack Easy Setup — Windows
REM  Double-click to install and run
REM ─────────────────────────────────────────────
cd /d "%~dp0"

echo.
echo  FaceTrack — Easy Setup (Windows)
echo =====================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found.
    echo Install Python 3.9+ from https://python.org  (check "Add to PATH")
    pause & exit /b 1
)

if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo Installing dependencies...
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo.
echo Starting FaceTrack...
echo Open: http://localhost:5000
echo.
python app.py
pause
