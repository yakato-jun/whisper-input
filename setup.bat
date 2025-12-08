@echo off
setlocal enabledelayedexpansion

echo Whisper Input Setup for Windows
echo ================================

where python >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is required but not found in PATH.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    exit /b 1
)

set VENV_DIR=.venv

if not exist "%VENV_DIR%" (
    echo Creating virtual environment at %VENV_DIR%
    python -m venv %VENV_DIR%
)

echo Activating virtual environment
call %VENV_DIR%\Scripts\activate.bat

echo Upgrading pip and installing Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Set your OpenAI API key:
echo    set OPENAI_API_KEY=your_api_key_here
echo.
echo 2. Run the application:
echo    %VENV_DIR%\Scripts\activate.bat
echo    python main.py
echo.
