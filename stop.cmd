@echo off
cd /d "%~dp0"
powershell -NoProfile -File "%~dp0stop.ps1"
pause
