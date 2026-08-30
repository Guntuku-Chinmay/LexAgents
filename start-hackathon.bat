@echo off
REM start-hackathon.bat
REM Starts the LexAgents hackathon environment via PowerShell wrapper

echo Checking for PowerShell...
where powershell.exe >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: powershell.exe not found in PATH.
    echo Running docker compose directly...
    docker compose down -v
    docker compose up --build
) else (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-hackathon.ps1"
)
pause
