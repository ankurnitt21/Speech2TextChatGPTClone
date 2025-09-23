@echo off
echo ========================================
echo   Speech2Text Background Service
echo ========================================

:: Check if config.ini exists
if not exist "config.ini" (
    echo ERROR: config.ini file not found!
    echo Please create a config.ini file with Redis and AssemblyAI credentials.
    pause
    exit /b 1
)

:: Check for different Python installations
echo Checking for Python installation...

:: Try python command first
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    echo Found Python: python
    goto :python_found
)

:: Try python3 command
python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python3
    echo Found Python: python3
    goto :python_found
)

:: Try py launcher (Windows Python Launcher)
py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    echo Found Python: py
    goto :python_found
)

:: No Python found
echo ERROR: Python is not installed or not in PATH!
echo Please install Python and ensure it's accessible from command line.
pause
exit /b 1

:python_found

:: Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found!
    echo Please ensure main.py is in the current directory.
    pause
    exit /b 1
)

:: Check if requirements.txt exists
if not exist "requirements.txt" (
    echo ERROR: requirements.txt not found!
    echo Please ensure requirements.txt is in the current directory.
    pause
    exit /b 1
)

echo Configuration file found: config.ini
echo Python installation found.
echo.

:: Install required dependencies from requirements.txt
echo Installing required dependencies from requirements.txt...
%PYTHON_CMD% -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo Warning: Some dependencies might not have installed correctly.
    echo You may need to install them manually if errors occur.
    echo.
)

:: Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

:: Get current timestamp for log file
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "YYYY=%dt:~0,4%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "HH=%dt:~8,2%" & set "Min=%dt:~10,2%" & set "Sec=%dt:~12,2%"
set "timestamp=%YYYY%-%MM%-%DD%_%HH%-%Min%-%Sec%"

echo Starting Speech2Text service in background...
echo Service will run in background with logs saved automatically.
echo.
echo To stop the service, run: manage_service.bat
echo.

:: Start the service completely hidden in background (no visible window)
powershell -WindowStyle Hidden -Command "Start-Process '%PYTHON_CMD%' -ArgumentList 'main.py' -WindowStyle Hidden"

echo ========================================
echo   Service Started Successfully!
echo ========================================
echo Service is now running in the background.
echo Logs will be created automatically in the logs\ directory.
echo.
echo Use manage_service.bat to stop the service.
echo Logs are automatically saved in the logs\ directory.
echo.
pause
