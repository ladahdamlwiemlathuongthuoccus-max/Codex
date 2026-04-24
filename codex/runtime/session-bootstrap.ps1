param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
)

$ErrorActionPreference = "Stop"

$required = @(
    "AGENTS.md",
    "codex\dispatcher.md",
    "codex\roles\operations-agent.md",
    "codex\roles\legal-agent.md",
    "codex\roles\accounting-agent.md",
    "codex\roles\strategy-agent.md",
    "codex\roles\evaluator-agent.md",
    ".mcp.json"
)

Write-Host "Agent Codex bootstrap"
Write-Host "Root: $Root"
Write-Host ""

foreach ($relative in $required) {
    $path = Join-Path $Root $relative
    if (Test-Path -LiteralPath $path) {
        Write-Host "OK   $relative"
    } else {
        Write-Host "MISS $relative"
    }
}

Write-Host ""
Write-Host "Next:"
Write-Host "1. Read AGENTS.md"
Write-Host "2. Read codex/dispatcher.md"
Write-Host "3. Run codex/evals/run-codex-smoke.ps1 after config/runtime changes"

