#!/bin/bash

echo "==================================================="
echo "Setting up Delulu Clone API (Linux/macOS)"
echo "==================================================="

echo "Checking for Python..."
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8+ and try again."
    return 1 2>/dev/null || true
fi

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt

echo "Installing additional production dependencies..."
pip install gunicorn python-dotenv psutil cryptography uvicorn[standard]

echo "Pre-downloading the AI model..."
python download_model.py

echo "==================================================="
echo "Setup complete!"
echo "To run the application in development:"
echo "  source venv/bin/activate"
echo "  python main.py"
echo "==================================================="
