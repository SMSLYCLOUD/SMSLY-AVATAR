@echo off
echo ===================================================
echo Setting up Delulu Clone API (Windows)
echo ===================================================

echo Checking for Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH. Please install Python 3.8+ and try again.
    goto :eof
)

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo Installing additional production dependencies...
pip install gunicorn python-dotenv psutil cryptography uvicorn[standard]

echo Pre-downloading the AI model...
python download_model.py

echo ===================================================
echo Setup complete!
echo To run the application in development:
echo   venv\Scripts\activate.bat
echo   python main.py
echo ===================================================
pause
