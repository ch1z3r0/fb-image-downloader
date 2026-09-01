@echo off
:: ============================================================
::  Facebook Image Downloader — One-Command Setup (Windows)
:: ============================================================
setlocal EnableDelayedExpansion

echo.
echo  ====================================================
echo   ^>  Facebook Image Downloader - Setup Script
echo  ====================================================
echo.

:: ---------- Check Python ----------
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Please install Python 3.9+ from https://www.python.org/downloads/
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% found

:: ---------- Create virtual environment ----------
if not exist ".venv\" (
    echo [*] Creating virtual environment...
    python -m venv .venv
)

:: ---------- Activate venv ----------
call .venv\Scripts\activate.bat
echo [OK] Virtual environment activated

:: ---------- Install dependencies ----------
echo [*] Installing Python dependencies...
pip install --upgrade pip -q
pip install -e . -q
pip install fastapi uvicorn pytest pytest-asyncio anyio httpx -q

:: ---------- Install Playwright ----------
echo [*] Installing Playwright Chromium browser...
python -m playwright install chromium

echo.
echo  ====================================================
echo    Setup complete! Ready to run.
echo  ====================================================
echo.
echo   Launch Web UI:
echo     .venv\Scripts\activate ^&^& python main.py --ui
echo.
echo   Then open http://localhost:8000 in your browser.
echo.
echo   To access from other devices on your Wi-Fi,
echo   open http://YOUR-PC-IP:8000 on the other device.
echo.
pause
