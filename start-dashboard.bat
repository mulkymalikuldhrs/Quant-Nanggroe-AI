@echo off
title Hedge Fund Dashboard
color 0A
cd /d E:\trading
echo Starting Hedge Fund Dashboard on http://localhost:5050
C:\Users\Hi\AppData\Local\hermes\hermes-agent\venv\Scripts\uvicorn dashboard:app --host 127.0.0.1 --port 5050 --reload
pause