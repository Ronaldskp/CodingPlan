@echo off
setlocal

cd /d "%~dp0"

if not exist "main.py" (
    echo [ERROR] main.py not found. Please check project directory.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
    echo [ERROR] requirements.txt not found.
    pause
    exit /b 1
)

if not exist "codingplan\Scripts\python.exe" (
    echo Creating virtual environment: codingplan
    python -m venv codingplan
    if errorlevel 1 goto :error
)

echo Installing project requirements...
echo For an exact validated environment, install requirements.lock.txt instead.
"codingplan\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo Installing kimi-code-usage...
"codingplan\Scripts\python.exe" -m pip install kimi-code-usage
if errorlevel 1 goto :error

echo Running doctor...
"codingplan\Scripts\python.exe" main.py doctor
if errorlevel 1 goto :error

echo.
echo Setup complete.
pause
exit /b 0

:error
echo.
echo [ERROR] Setup failed. Review the output above and try again.
pause
exit /b 1
