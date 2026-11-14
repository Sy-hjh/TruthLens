$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$existing = $null
try { $existing = Invoke-RestMethod 'http://127.0.0.1:8010/api/health' -TimeoutSec 2 } catch { }
if ($existing) {
    if ($existing.version -eq '3.0.0') { Write-Host 'TruthLens 真鉴已经运行：http://127.0.0.1:8010'; exit 0 }
    throw '8010端口已有其他或旧版本服务，请先关闭该服务。'
}
New-Item -ItemType Directory -Force runtime | Out-Null
$configuredPython = Join-Path $PSScriptRoot 'runtime/python-path.txt'
$pythonPath = if (Test-Path -LiteralPath $configuredPython) {
    $selectedPython = (Get-Content -LiteralPath $configuredPython -Raw).Trim()
    if (-not (Test-Path -LiteralPath $selectedPython -PathType Leaf)) { throw 'Configured project Python was not found.' }
    $selectedPython
} elseif (Test-Path .venv/Scripts/python.exe) { (Resolve-Path .venv/Scripts/python.exe).Path } else { (Get-Command python).Source }
$scriptPath = Join-Path $PSScriptRoot 'run.py'
$process = Start-Process -FilePath $pythonPath -ArgumentList @('-u', ('"' + $scriptPath + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'runtime/server.log') -RedirectStandardError (Join-Path $PSScriptRoot 'runtime/server-error.log') -PassThru
$process.Id | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime/server.pid')
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 500
    try {
        $health = Invoke-RestMethod 'http://127.0.0.1:8010/api/health' -TimeoutSec 2
        if ($health.version -eq '3.0.0') { Write-Host 'TruthLens 真鉴已启动：http://127.0.0.1:8010'; exit 0 }
    } catch { }
}
throw '启动未成功，请查看runtime/server-error.log。'
