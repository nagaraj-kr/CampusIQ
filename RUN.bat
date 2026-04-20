@echo off
REM College Recommendation System - Quick Start Script (Windows)
setlocal enabledelayedexpansion

echo.
echo ================================================================================
echo     COLLEGE RECOMMENDATION SYSTEM - QUICK START
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org
    pause
    exit /b 1
)

REM Check if Node is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo WARNING: Node.js is not installed. Frontend will not run.
    echo Download from https://nodejs.org/
    echo.
) else (
    echo OK: Node.js is installed
)

echo.
echo Step 1: Setting up Python environment...
cd /d "%~dp0\college_recommendation_system\backend"

if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
) else (
    echo Virtual environment already exists
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -q -r requirements.txt 2>nul
if errorlevel 1 (
    echo WARNING: Could not install from requirements.txt
    echo Installing manually...
    pip install -q django djangorestframework django-cors-headers python-decouple requests groq
)

echo.
echo Step 2: Database check...
if exist "db.sqlite3" (
    echo Database exists (500 colleges, 1,659 courses)
) else (
    echo Running migrations...
    python manage.py migrate --quiet
)

echo.
echo ================================================================================
echo.
echo READY TO START!
echo.
echo TERMINAL 1 - START BACKEND API:
echo   cd college_recommendation_system\backend
echo   venv\Scripts\activate
echo   python manage.py runserver
echo.
echo   Backend will run at: http://localhost:8000
echo.
echo TERMINAL 2 - START FRONTEND (optional):
echo   cd college_recommendation_system\college-chatbot
echo   npm install  (first time only)
echo   npm run dev
echo.
echo   Frontend will run at: http://localhost:5173
echo.
echo ================================================================================
echo.
echo Test the API with any course type:
echo   - IT, Information Technology, CSE, Computer Science
echo   - Mechanical, Civil, Electrical, B.Sc, BCA
echo   - MBA, B.Com, Electrical Engineering
echo.
echo ================================================================================
pause
