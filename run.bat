@echo off
echo ========================================
echo   Khusboo Creatives - AI Agent
echo ========================================

if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and add your API key.
    pause
    exit /b 1
)

pip install -r requirements.txt --quiet

echo.
echo Starting server at http://localhost:5000
echo Dashboard at  http://localhost:5000/dashboard
echo Password:     khusboo2024
echo.
echo Press Ctrl+C to stop.
echo.

python app.py
pause
