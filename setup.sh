#!/bin/bash
# Image-to-Speech setup script
set -e

echo "============================================="
echo "Initializing Image-to-Speech MVP Environment"
echo "============================================="

# Ensure we're in the project directory
cd "$(dirname "$0")"

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but was not found on your system."
    exit 1
fi

echo "1. Creating Python virtual environment (venv)..."
python3 -m venv venv

echo "2. Activating venv and upgrading pip..."
source venv/bin/activate
python3 -m pip install --upgrade pip

echo "3. Installing project dependencies..."
pip install -r requirements.txt

if [ ! -f .env ]; then
    echo "4. Generating local .env file..."
    cp .env.example .env
    echo "-----------------------------------------------"
    echo "SETUP SUCCESSFUL!"
    echo "Please open '.env' and paste your GEMINI_API_KEY."
    echo "-----------------------------------------------"
else
    echo "4. .env file already exists. Skipping creation."
    echo "-----------------------------------------------"
    echo "SETUP SUCCESSFUL!"
    echo "-----------------------------------------------"
fi
