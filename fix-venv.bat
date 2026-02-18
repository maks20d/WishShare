@echo off
REM Script to fix virtual environment issues
REM Recreates venv and installs dependencies correctly

echo ========================================
echo   WishShare - Fix Virtual Environment
echo ========================================
echo.

cd backend

REM Remove old venv if exists
if exist ".venv" (
    echo [INFO] Removing old virtual environment...
    rmdir /s /q .venv
)

REM Create new venv
echo [INFO] Creating new virtual environment...
python -m venv .venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

REM Install using venv Python directly
echo [INFO] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo [INFO] Installing dependencies...
.venv\Scripts\python.exe -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [INFO] Installing Playwright browsers...
.venv\Scripts\python.exe -m playwright install chromium

echo.
echo [OK] Virtual environment fixed successfully!
echo.
cd ..
pause
