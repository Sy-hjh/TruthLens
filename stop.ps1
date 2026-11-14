$ErrorActionPreference = 'Stop'
$pidFile = Join-Path $PSScriptRoot 'runtime/server.pid'
if (-not (Test-Path -LiteralPath $pidFile)) { Write-Host '没有后台启动记录。'; exit 0 }
$servicePid = [int](Get-Content -LiteralPath $pidFile)
$process = Get-CimInstance Win32_Process -Filter "ProcessId = $servicePid"
if (-not $process) { Remove-Item -LiteralPath $pidFile; Write-Host '服务已经停止。'; exit 0 }
$scriptPath = Join-Path $PSScriptRoot 'run.py'
if (-not $process.CommandLine -or $process.CommandLine.IndexOf($scriptPath, [StringComparison]::OrdinalIgnoreCase) -lt 0) { throw '进程标识不匹配，未停止任何进程。' }
$voiceWorkerPath = Join-Path $PSScriptRoot 'backend/verispoof_worker.py'
$voiceChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId = $servicePid" | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -and $_.CommandLine.IndexOf($voiceWorkerPath, [StringComparison]::OrdinalIgnoreCase) -ge 0 }
foreach ($voiceChild in $voiceChildren) { Stop-Process -Id $voiceChild.ProcessId -ErrorAction SilentlyContinue }
Stop-Process -Id $servicePid
Remove-Item -LiteralPath $pidFile
Write-Host 'TruthLens 真鉴后台服务已停止。'
