#!/bin/bash
cd "$(dirname "$0")"

# Load environment variables from .env if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check required environment variables
if [ -z "$GOOGLE_SHEET_ID" ]; then
    echo "ERROR: GOOGLE_SHEET_ID not set in .env file"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

if [ -z "$GOG_ACCOUNT" ]; then
    echo "ERROR: GOG_ACCOUNT not set in .env file"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data/history data/routines

# Run the app
PORT=${PORT:-5561}
echo "Starting CANSLIM Scanner Dashboard on http://localhost:$PORT"
python app.py
