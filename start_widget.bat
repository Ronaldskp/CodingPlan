@echo off
setlocal

cd /d "%~dp0"

if not exist "codingplan\Scripts\python.exe" (
    echo [ERROR] codingplan virtual environment not found.
    echo Please run:
    echo   cd /d "%~dp0"
    echo   python -m venv codingplan
    echo   codingplan\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "main.py" (
    echo [ERROR] main.py not found. Please check project directory.
    pause
    exit /b 1
)

echo Debug launcher. For silent desktop launch, use start_widget_silent.vbs or desktop shortcut.
echo Starting CodingPlanWidget...
"codingplan\Scripts\python.exe" main.py widget

if errorlevel 1 (
    echo.
    echo [ERROR] CodingPlanWidget exited with an error.
    pause
    exit /b 1
)

endlocal
