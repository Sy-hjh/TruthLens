@echo off
cd /d "%~dp0"
if not exist data\balanced-v1\manifest.json (
  echo Dataset is not ready. Check runtime\balanced-download.log
  pause
  exit /b 1
)
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe train_images.py --manifest data/balanced-v1/manifest.json --output models/balanced-v1 --epochs 20 --patience 5
) else (
  python train_images.py --manifest data/balanced-v1/manifest.json --output models/balanced-v1 --epochs 20 --patience 5
)
pause
