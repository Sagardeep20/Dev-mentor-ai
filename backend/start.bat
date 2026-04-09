@echo off
title DevMentor AI Backend
color 0A

echo ==================================================
echo  DevMentor AI - Backend Server Starter
echo ==================================================
echo.

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    echo.
)

REM Activate venv
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Install dependencies
echo [3/4] Installing dependencies...
pip install -r requirements.txt >nul 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)
echo.

REM Check for .env file
if not exist ".env" (
    echo [WARNING] .env file not found. Creating from .env.example...
    copy .env.example .env >nul 2>&1
    echo [WARNING] Please edit .env and add your GROQ_API_KEY
    echo.
)

REM Check for GROQ_API_KEY
findstr /C:"GROQ_API_KEY=your-groq-api-key-here" .env >nul 2>&1
if %errorlevel%==0 (
    echo ================================================
    echo  WARNING: GROQ_API_KEY not set!
    echo ================================================
    echo 1. Edit .env file
    echo 2. Replace 'your-groq-api-key-here' with your actual key
    echo 3. Get free key at: https://console.groq.com/keys
    echo ================================================
    echo.
)

REM Start server
echo [4/4] Starting DevMentor API Server...
echo.
echo Server will run at: http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

python main.py
