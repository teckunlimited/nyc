#!/bin/bash
# Backend startup script for npm integration

set -e

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/.installed" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
    touch venv/.installed
fi

# Set database URL
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/nycdb"

# Start backend
echo "Starting backend server on http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
