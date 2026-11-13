$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$config = Join-Path $PSScriptRoot 'runtime/python-path.txt'
$agentPython = if (Test-Path -LiteralPath $config) { (Get-Content -LiteralPath $config -Raw).Trim() } else { (Get-Command python).Source }
& $agentPython -m pip install --target .agent-packages --upgrade -r requirements-agent.txt
if ($LASTEXITCODE -ne 0) { throw 'Agent dependency installation failed.' }
& $agentPython -c 'import bootstrap; from langchain.agents import create_agent; from backend.agent_model import LocalQwenTools; print("LangChain Agent ready")'
if ($LASTEXITCODE -ne 0) { throw 'Agent import check failed.' }
