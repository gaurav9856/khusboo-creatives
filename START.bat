@echo off
title Khusboo Creatives - AI Agent Launcher
color 0D

echo.
echo  ==========================================
echo   Khusboo Creatives - AI Agent Launcher
echo  ==========================================
echo.

REM Check .env has real API key
findstr /C:"paste_your_key_here" .env >nul 2>&1
if %errorlevel%==0 (
    echo  ERROR: Please open .env file and replace
    echo  'paste_your_key_here' with your real API key.
    echo.
    notepad .env
    pause
    exit /b 1
)

echo  Starting Flask app...
start "Flask App" cmd /k "cd /d %~dp0 && python app.py"

timeout /t 3 /nobreak >nul

echo  Starting ngrok tunnel...
start "ngrok Tunnel" cmd /k "cd /d %~dp0 && ngrok.exe http 5000"

timeout /t 4 /nobreak >nul

echo  Opening browser...
start http://localhost:5000

echo.
echo  ==========================================
echo   Everything is running!
echo.
echo   Local:     http://localhost:5000
echo   Dashboard: http://localhost:5000/dashboard
echo   Password:  khusboo2024
echo.
echo   Check the ngrok window for your
echo   public shareable URL!
echo  ==========================================
echo.
pause
