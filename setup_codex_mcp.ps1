$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$McpJson = Join-Path $Root ".mcp.json"
$PackageJson = Join-Path $Root "package.json"
$NodeModules = Join-Path $Root "node_modules"

Write-Host "Agent Codex MCP setup/check"
Write-Host "Root: $Root"

if (-not (Test-Path -LiteralPath $PackageJson)) {
    throw "package.json not found"
}

if (-not (Test-Path -LiteralPath $NodeModules)) {
    Write-Host "node_modules not found; running npm install"
    npm install
}

$config = Get-Content -LiteralPath $McpJson -Raw | ConvertFrom-Json
$servers = $config.mcpServers.PSObject.Properties.Name

foreach ($server in $servers) {
    $entry = $config.mcpServers.$server
    $script = Join-Path $Root ($entry.args[0] -replace "/", "\")
    if (-not (Test-Path -LiteralPath $script)) {
        throw "MCP server script not found for ${server}: $script"
    }
    Write-Host "OK $server -> $script"
}

Write-Host "OK Agent Codex MCP files are present."

