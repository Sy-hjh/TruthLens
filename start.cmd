@echo off
cd /d "%~dp0"
set "QINAN_PYTHON=python"
if exist .venv\Scripts\python.exe set "QINAN_PYTHON=.venv\Scripts\python.exe"
if exist runtime\python-path.txt set /p QINAN_PYTHON=<runtime\python-path.txt
"%QINAN_PYTHON%" run.py
pause
