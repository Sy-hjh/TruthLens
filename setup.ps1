$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force runtime/tmp | Out-Null
$env:TEMP = (Resolve-Path runtime/tmp).Path
$env:TMP = $env:TEMP
# Bundled OCR/MMCV extensions target CPython 3.10; reject incompatible defaults.
$projectPython = if (Get-Command py -ErrorAction SilentlyContinue) { 'py' } else { 'python' }
$versionArgs = if ($projectPython -eq 'py') { @('-3.10') } else { @() }
& $projectPython @versionArgs -c "import sys; assert sys.version_info[:2] == (3,10), 'TruthLens requires Python 3.10 for its packaged native extensions'"
if ($LASTEXITCODE -ne 0) { throw '请先安装 Python 3.10 x64，并确认 py -3.10 可用。' }
& $projectPython @versionArgs -m venv .venv
if ($LASTEXITCODE -ne 0) { throw '创建Python环境失败' }
& .venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '安装依赖失败，请检查网络' }
Write-Host '安装完成；使用 .venv/Scripts/python.exe run.py 或双击start.cmd。CUDA版PyTorch请按驱动兼容版本安装。'
