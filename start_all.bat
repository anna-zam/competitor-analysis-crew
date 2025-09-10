@echo off
echo Starting Competitor Analysis System...
echo.

echo Starting Backend Server in new window...
start "Backend Server" cmd /k "cd /d %~dp0 && uvicorn backend.main:app --reload --port 8000"

echo Waiting 5 seconds for backend to start...
timeout /t 5 /nobreak > nul

echo Starting Frontend Server in new window...
start "Frontend Server" cmd /k "cd /d %~dp0\frontend && npm run dev"

echo.
echo Both servers are starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit...
pause > nul
