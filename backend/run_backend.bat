@echo off
REM Mutual Fund Chatbot backend - port 8001 (avoids conflict with other services on 8000)
cd /d "%~dp0"
uvicorn main:app --reload --port 8001
