@echo off
echo ========================================
echo   Stop Speech2Text Service
echo ========================================

echo Stopping Speech2Text background service...

:: First try to kill Python processes running main.py by command line
wmic process where "name='python.exe' and commandline like '%main.py%'" delete >nul 2>&1
wmic process where "name='python3.exe' and commandline like '%main.py%'" delete >nul 2>&1
wmic process where "name='py.exe' and commandline like '%main.py%'" delete >nul 2>&1

:: Wait a moment for processes to terminate
timeout /t 2 /nobreak >nul

:: Check if any Python processes are still running and kill them as backup
tasklist /fi "imagename eq python.exe" /fo csv /nh 2>nul | findstr /i "python.exe" >nul
if not errorlevel 1 (
    echo Found remaining Python processes, terminating...
    taskkill /f /im python.exe >nul 2>&1
)

tasklist /fi "imagename eq python3.exe" /fo csv /nh 2>nul | findstr /i "python3.exe" >nul
if not errorlevel 1 (
    echo Found remaining Python3 processes, terminating...
    taskkill /f /im python3.exe >nul 2>&1
)

tasklist /fi "imagename eq py.exe" /fo csv /nh 2>nul | findstr /i "py.exe" >nul
if not errorlevel 1 (
    echo Found remaining Py processes, terminating...
    taskkill /f /im py.exe >nul 2>&1
)

echo Service stopped successfully.

echo.
echo ========================================
echo   Service Stopped
echo ========================================
echo Speech2Text service has been stopped.
echo.

:: Show available log files
if exist "logs\*.log" (
    echo Available log files in logs\ directory:
    dir /b logs\speech2text_*.log 2>nul
    echo.
    echo You can view any log file by opening it directly.
) else (
    echo No log files found in logs\ directory.
)

pause