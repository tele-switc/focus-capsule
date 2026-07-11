@echo off
chcp 65001 >nul
echo ========================================
echo   Focus Capsule - Installation
echo ========================================
echo.

echo Installing Python dependencies...
python -m pip install --quiet --user -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo Please ensure Python 3.10+ is installed.
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.
echo To start Focus Capsule, run:
echo   python -m focus_capsule
echo.
echo Or double-click: run.bat
echo.
pause
