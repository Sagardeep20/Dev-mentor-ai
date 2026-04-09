#!/bin/bash

# DevMentor AI - Backend Server Starter (Unix/Mac/Linux)

echo "=================================================="
echo " DevMentor AI - Backend Server Starter"
echo "=================================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "[1/4] Creating virtual environment..."
    python3 -m venv venv
    echo ""
fi

# Activate venv
echo "[2/4] Activating virtual environment..."
source venv/bin/activate
echo ""

# Install dependencies
echo "[3/4] Installing dependencies..."
pip install -r requirements.txt > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    echo "Please run: pip install -r requirements.txt"
    read -p "Press Enter to continue..."
    exit 1
fi
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "[WARNING] Please edit .env and add your GROQ_API_KEY"
    echo ""
fi

# Check for GROQ_API_KEY
if grep -q "your-groq-api-key-here" .env; then
    echo "================================================"
    echo " WARNING: GROQ_API_KEY not set!"
    echo "================================================"
    echo "1. Edit .env file"
    echo "2. Replace 'your-groq-api-key-here' with your actual key"
    echo "3. Get free key at: https://console.groq.com/keys"
    echo "================================================"
    echo ""
fi

# Start server
echo "[4/4] Starting DevMentor API Server..."
echo ""
echo "Server will run at: http://localhost:8000"
echo "API docs at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
