#!/usr/bin/env bash
# Mutual Fund Chatbot backend - port 8001 (avoids conflict with other services on 8000)
cd "$(dirname "$0")"
uvicorn main:app --reload --port 8001
