$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force runtime/tmp | Out-Null
$env:TEMP = (Resolve-Path runtime/tmp).Path
$env:TMP = $env:TEMP
python -m venv .venv
if ($LASTEXITCODE -ne 0) { throw '创建Python环境失败' }
& .venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw '安装依赖失败，请检查网络' }
Write-Host '安装完成；使用 .venv/Scripts/python.exe run.py 或双击start.cmd。CUDA版PyTorch请按驱动兼容版本安装。'
