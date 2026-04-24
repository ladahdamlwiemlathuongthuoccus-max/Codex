$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = (Resolve-Path (Join-Path $ScriptRoot "..\..\..")).Path
$VenvPython = "C:\Users\sashatrash\.codex\plugins\cache\local\agenthq-local-control\1.0.0\.venv\Scripts\python.exe"
$ServerPath = Join-Path $ScriptRoot "agenthq_local_control_mcp.py"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Error "Local Control venv not found: $VenvPython"
    exit 1
}

if (-not (Test-Path -LiteralPath $ServerPath)) {
    Write-Error "MCP server script not found: $ServerPath"
    exit 1
}

$env:PYTHONUTF8 = "1"
$env:AGENT_CODEX_ROOT = $ProjectRoot
$env:AGENT_CODEX_BROWSER_ROOT = Join-Path $ProjectRoot "codex\browser"

& $VenvPython $ServerPath
exit $LASTEXITCODE

