#!/bin/bash
# College Recommendation System - Quick Start Script (Mac/Linux)

echo ""
echo "================================================================================"
echo "    COLLEGE RECOMMENDATION SYSTEM - QUICK START"
echo "================================================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed or not in PATH"
    echo "Please install Python 3.8+ from https://www.python.org"
    exit 1
fi

# Check if Node is installed
if ! command -v node &> /dev/null; then
    echo "WARNING: Node.js is not installed. Frontend will not run."
    echo "Download from https://nodejs.org/"
    echo ""
else
    echo "OK: Node.js is installed"
fi

echo ""
echo "Step 1: Setting up Python environment..."
cd "$(dirname "$0")/college_recommendation_system/backend"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "Virtual environment already exists"
fi

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing dependencies..."
pip install -q -r requirements.txt 2>/dev/null || {
    echo "WARNING: Could not install from requirements.txt"
    echo "Installing manually..."
    pip install -q django djangorestframework django-cors-headers python-decouple requests groq
}

echo ""
echo "Step 2: Database check..."
if [ -f "db.sqlite3" ]; then
    echo "Database exists (500 colleges, 1,659 courses)"
else
    echo "Running migrations..."
    python manage.py migrate --quiet
fi

echo ""
echo "================================================================================"
echo ""
echo "READY TO START!"
echo ""
echo "TERMINAL 1 - START BACKEND API:"
echo "  cd college_recommendation_system/backend"
echo "  source venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "  Backend will run at: http://localhost:8000"
echo ""
echo "TERMINAL 2 - START FRONTEND (optional):"
echo "  cd college_recommendation_system/college-chatbot"
echo "  npm install  (first time only)"
echo "  npm run dev"
echo ""
echo "  Frontend will run at: http://localhost:5173"
echo ""
echo "================================================================================"
echo ""
echo "Test the API with any course type:"
echo "  - IT, Information Technology, CSE, Computer Science"
echo "  - Mechanical, Civil, Electrical, B.Sc, BCA"
echo "  - MBA, B.Com, Electrical Engineering"
echo ""
echo "================================================================================"
