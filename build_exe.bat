@echo off
setlocal

cd /d E:\Ronald\CodingPlanWidget

if not exist "codingplan\Scripts\python.exe" (
    echo [ERROR] codingplan virtual environment not found.
    echo Please run setup_env.bat first.
    pause
    exit /b 1
)

set PYTHON=codingplan\Scripts\python.exe

echo Installing / verifying PyInstaller...
"%PYTHON%" -m pip install pyinstaller
if errorlevel 1 (
    echo [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release\CodingPlanWidget rmdir /s /q release\CodingPlanWidget

echo Building EXE...
"%PYTHON%" -m PyInstaller CodingPlanWidget.spec
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

echo Preparing release folder...
mkdir release\CodingPlanWidget
mkdir release\CodingPlanWidget\data
mkdir release\CodingPlanWidget\assets

xcopy /e /i /y dist\CodingPlanWidget release\CodingPlanWidget
if errorlevel 1 (
    echo [ERROR] Failed to copy dist files to release.
    pause
    exit /b 1
)

copy /y config.yaml release\CodingPlanWidget\config.yaml
copy /y .env.example release\CodingPlanWidget\.env.example
copy /y assets\coding_plan.ico release\CodingPlanWidget\assets\coding_plan.ico

echo Generating data placeholders and README...
"%PYTHON%" scripts\generate_release_files.py "release\CodingPlanWidget"
if errorlevel 1 (
    echo [ERROR] Failed to generate release files.
    pause
    exit /b 1
)

echo.
echo CodingPlanWidget release created:
echo E:\Ronald\CodingPlanWidget\release\CodingPlanWidget

pause
endlocal
