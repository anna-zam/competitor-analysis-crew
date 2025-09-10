@echo off
echo Starting Backend Server...
cd /d "%~dp0"
uvicorn backend.main:app --reload --port 8000
pause
