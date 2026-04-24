param(
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$RunId = Get-Date -Format "yyyyMMdd-HHmmss"
$RunDir = Join-Path $PSScriptRoot "runs\$RunId"
New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

$Failures = New-Object System.Collections.Generic.List[string]
$Warnings = New-Object System.Collections.Generic.List[string]
$Passes = New-Object System.Collections.Generic.List[string]
$LevelResults = New-Object System.Collections.Generic.List[object]

function Add-Pass($Level, $Message) {
    $Passes.Add("$Level $Message") | Out-Null
    Write-Host "PASS [$Level] $Message"
}

function Add-Warn($Level, $Message) {
    $Warnings.Add("$Level $Message") | Out-Null
    Write-Host "WARN [$Level] $Message"
}

function Add-Fail($Level, $Message) {
    $Failures.Add("$Level $Message") | Out-Null
    Write-Host "FAIL [$Level] $Message"
}

function Test-RequiredPath($Level, $Relative) {
    $path = Join-Path $Root $Relative
    if (Test-Path -LiteralPath $path) {
        Add-Pass $Level "exists: $Relative"
    } else {
        Add-Fail $Level "missing: $Relative"
    }
}

function Test-JsonFile($Level, $Relative) {
    $path = Join-Path $Root $Relative
    try {
        Get-Content -LiteralPath $path -Raw | ConvertFrom-Json | Out-Null
        Add-Pass $Level "valid json: $Relative"
    } catch {
        Add-Fail $Level "invalid json: $Relative :: $($_.Exception.Message)"
    }
}

function Test-PowerShellSyntax($Level, $Relative) {
    $path = Join-Path $Root $Relative
    $tokens = $null
    $errors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors) | Out-Null
    if ($errors.Count -eq 0) {
        Add-Pass $Level "valid powershell syntax: $Relative"
    } else {
        Add-Fail $Level "powershell syntax errors: $Relative"
    }
}

function Complete-Level($Level, $BeforeFailures, $BeforeWarnings) {
    $newFailures = $Failures.Count - $BeforeFailures
    $newWarnings = $Warnings.Count - $BeforeWarnings
    $status = if ($newFailures -gt 0) { "FAIL" } elseif ($Strict -and $newWarnings -gt 0) { "FAIL" } elseif ($newWarnings -gt 0) { "WARN" } else { "PASS" }
    $LevelResults.Add([ordered]@{
        level = $Level
        status = $status
        failures = $newFailures
        warnings = $newWarnings
    }) | Out-Null
}

Write-Host "Agent Codex L0-L7 smoke"
Write-Host "Root: $Root"
Write-Host "Run:  $RunDir"
Write-Host ""

# L0: structure and source-of-truth
$bf = $Failures.Count; $bw = $Warnings.Count
@(
    "AGENTS.md",
    "CLAUDE.md",
    "codex\README.md",
    "codex\dispatcher.md",
    "codex\migration\inventory.md",
    "codex\runtime\path-policy.md",
    "codex\runtime\browser-policy.md",
    "codex\runtime\verification-policy.md",
    "codex\mcp\README.md",
    "codex\mcp\codex-config.example.toml",
    "codex\mcp\local-control-config.example.toml",
    "codex\mcp\local-control\start-mcp.ps1",
    "codex\mcp\local-control\agenthq_local_control_mcp.py",
    "codex\mcp\local-control\smoke-client.py",
    "codex\browser\scenarios\smoke-local-form.json",
    "codex\browser\assets\smoke-form.html",
    "codex\evals\run-mcp-client-smoke.py",
    ".mcp.json",
    "package.json"
) | ForEach-Object { Test-RequiredPath "L0" $_ }

$roleFiles = Get-ChildItem -LiteralPath (Join-Path $Root "codex\roles") -File -Filter "*.md" -ErrorAction SilentlyContinue
$skillDirs = Get-ChildItem -LiteralPath (Join-Path $Root "codex\skills") -Directory -ErrorAction SilentlyContinue
$commandFiles = Get-ChildItem -LiteralPath (Join-Path $Root "codex\commands") -File -Filter "*.md" -ErrorAction SilentlyContinue
if ($roleFiles.Count -ge 5) { Add-Pass "L0" "roles count >= 5 ($($roleFiles.Count))" } else { Add-Fail "L0" "roles count < 5 ($($roleFiles.Count))" }
if ($skillDirs.Count -ge 25) { Add-Pass "L0" "skills count >= 25 ($($skillDirs.Count))" } else { Add-Fail "L0" "skills count < 25 ($($skillDirs.Count))" }
if ($commandFiles.Count -ge 6) { Add-Pass "L0" "commands count >= 6 ($($commandFiles.Count))" } else { Add-Fail "L0" "commands count < 6 ($($commandFiles.Count))" }
Complete-Level "L0" $bf $bw

# L1: JSON/TOML/PowerShell config validity
$bf = $Failures.Count; $bw = $Warnings.Count
@(
    ".mcp.json",
    "codex\mcp\agent-codex.mcp.json",
    "codex\evals\routing_cases.json",
    "codex\browser\scenarios\smoke-local-form.json"
) | ForEach-Object { Test-JsonFile "L1" $_ }

@(
    "codex\evals\run-codex-smoke.ps1",
    "codex\runtime\session-bootstrap.ps1",
    "codex\mcp\local-control\start-mcp.ps1",
    "setup_codex_mcp.ps1"
) | ForEach-Object { Test-PowerShellSyntax "L1" $_ }

foreach ($toml in @("codex\mcp\codex-config.example.toml", "codex\mcp\local-control-config.example.toml")) {
    $text = Get-Content -LiteralPath (Join-Path $Root $toml) -Raw
    if ($text -match "\[mcp_servers\.") { Add-Pass "L1" "toml has mcp_servers section: $toml" } else { Add-Fail "L1" "toml missing mcp_servers section: $toml" }
}
Complete-Level "L1" $bf $bw

# L2: MCP smoke
$bf = $Failures.Count; $bw = $Warnings.Count
try {
    $mcp = Get-Content -LiteralPath (Join-Path $Root ".mcp.json") -Raw | ConvertFrom-Json
    $serverNames = $mcp.mcpServers.PSObject.Properties.Name
    foreach ($server in $serverNames) {
        $entry = $mcp.mcpServers.$server
        $script = Join-Path $Root ($entry.args[0] -replace "/", "\")
        if (Test-Path -LiteralPath $script) { Add-Pass "L2" "mcp script exists: $server" } else { Add-Fail "L2" "mcp script missing: $server -> $script" }
    }
    $mcpText = Get-Content -LiteralPath (Join-Path $Root ".mcp.json") -Raw
    if ($mcpText -match "Agent systems/AgentHQ|Agent systems\\AgentHQ") { Add-Fail "L2" ".mcp.json points to original AgentHQ" } else { Add-Pass "L2" ".mcp.json does not point to original AgentHQ" }
} catch {
    Add-Fail "L2" ".mcp.json parse failed: $($_.Exception.Message)"
}

try {
    $nodeVersion = (& node --version) 2>$null
    if ($LASTEXITCODE -eq 0 -and $nodeVersion) { Add-Pass "L2" "node available: $nodeVersion" } else { Add-Warn "L2" "node not available in PATH" }
} catch {
    Add-Warn "L2" "node check failed: $($_.Exception.Message)"
}
Complete-Level "L2" $bf $bw

# L3: routing cases
$bf = $Failures.Count; $bw = $Warnings.Count
$dispatcher = Get-Content -LiteralPath (Join-Path $Root "codex\dispatcher.md") -Raw
foreach ($needle in @("operations-agent", "legal-agent", "accounting-agent", "strategy-agent", "evaluator-agent", "browser-use", "documents", "spreadsheets", "openai-codex")) {
    if ($dispatcher -match [regex]::Escape($needle)) { Add-Pass "L3" "dispatcher contains: $needle" } else { Add-Fail "L3" "dispatcher missing: $needle" }
}

$cases = (Get-Content -LiteralPath (Join-Path $PSScriptRoot "routing_cases.json") -Raw | ConvertFrom-Json).cases
foreach ($case in $cases) {
    if ($dispatcher -match [regex]::Escape($case.expected)) {
        Add-Pass "L3" "routing case $($case.id) -> $($case.expected)"
    } else {
        Add-Fail "L3" "routing case $($case.id) missing expected target $($case.expected)"
    }
}
Complete-Level "L3" $bf $bw

# L4: document workflow replacement
$bf = $Failures.Count; $bw = $Warnings.Count
foreach ($needle in @('Codex `documents`', 'Codex `pdf`', 'Codex `presentations`', 'Codex `spreadsheets`')) {
    if ($dispatcher -match [regex]::Escape($needle)) { Add-Pass "L4" "document replacement present: $needle" } else { Add-Fail "L4" "document replacement missing: $needle" }
}

foreach ($relative in @("codex\commands\fsi-report.md", "codex\commands\pitch-deck.md", "codex\skills\pitch-deck\SKILL.md")) {
    $text = Get-Content -LiteralPath (Join-Path $Root $relative) -Raw
    if ($text -match "anthropic-skills") { Add-Fail "L4" "active document workflow still references anthropic-skills: $relative" } else { Add-Pass "L4" "no anthropic-skills in active document workflow: $relative" }
}
Complete-Level "L4" $bf $bw

# L5: browser workflow without sensitive submit
$bf = $Failures.Count; $bw = $Warnings.Count
$browserPolicy = Get-Content -LiteralPath (Join-Path $Root "codex\runtime\browser-policy.md") -Raw
foreach ($needle in @("Prepare", "Evidence", "Review", "Confirm", "Submit", "Verify")) {
    if ($browserPolicy -match [regex]::Escape($needle)) { Add-Pass "L5" "browser policy step present: $needle" } else { Add-Fail "L5" "browser policy step missing: $needle" }
}

$scenario = Get-Content -LiteralPath (Join-Path $Root "codex\browser\scenarios\smoke-local-form.json") -Raw | ConvertFrom-Json
if ($scenario.sensitiveActionsAllowed -eq $false) { Add-Pass "L5" "browser smoke blocks sensitive actions" } else { Add-Fail "L5" "browser smoke allows sensitive actions" }
if ($scenario.blockedSensitiveStep.requiresFinalConfirmation -eq $true) { Add-Pass "L5" "browser smoke requires final confirmation for submit" } else { Add-Fail "L5" "browser smoke missing final confirmation" }
Complete-Level "L5" $bf $bw

# L6: path-safety
$bf = $Failures.Count; $bw = $Warnings.Count
$rootNormalized = [System.IO.Path]::GetFullPath($Root)
if ($rootNormalized -eq "D:\REDPEAK\Agent systems\Agent for Codex\Agent Codex") { Add-Pass "L6" "root is Agent Codex" } else { Add-Fail "L6" "unexpected root: $rootNormalized" }

$activeConfigFiles = @(
    ".mcp.json",
    ".claude\settings.json",
    "setup_codex_mcp.ps1",
    "setup_mcp.bat",
    "codex\mcp\agent-codex.mcp.json",
    "codex\mcp\codex-config.example.toml"
)
foreach ($relative in $activeConfigFiles) {
    $path = Join-Path $Root $relative
    if (Test-Path -LiteralPath $path) {
        $text = Get-Content -LiteralPath $path -Raw
        if ($text -match "D:/REDPEAK/Agent systems/AgentHQ|D:\\REDPEAK\\Agent systems\\AgentHQ") {
            Add-Fail "L6" "active config points to original AgentHQ: $relative"
        } else {
            Add-Pass "L6" "active config does not point to original AgentHQ: $relative"
        }
    }
}

$pathPolicy = Get-Content -LiteralPath (Join-Path $Root "codex\runtime\path-policy.md") -Raw
if ($pathPolicy -match "отдельного явного разрешения" -and $pathPolicy -match "AgentHQ") {
    Add-Pass "L6" "path policy protects outside writes and original AgentHQ"
} else {
    Add-Fail "L6" "path policy missing outside-write/original protections"
}
Complete-Level "L6" $bf $bw

# L7: regression report gate
$bf = $Failures.Count; $bw = $Warnings.Count
if ($Failures.Count -eq 0) { Add-Pass "L7" "all critical checks passed before report" } else { Add-Fail "L7" "critical failures exist before report" }
if ($Warnings.Count -eq 0) { Add-Pass "L7" "no warnings before report" } else { Add-Warn "L7" "warnings present before report: $($Warnings.Count)" }
Complete-Level "L7" $bf $bw

$report = [ordered]@{
    runId = $RunId
    root = $Root
    strict = [bool]$Strict
    levels = $LevelResults
    passes = $Passes.Count
    warnings = $Warnings
    failures = $Failures
}

$reportJson = $report | ConvertTo-Json -Depth 8
$jsonPath = Join-Path $RunDir "smoke-report.json"
$mdPath = Join-Path $RunDir "regression-report.md"
$reportJson | Set-Content -LiteralPath $jsonPath -Encoding UTF8

$md = New-Object System.Collections.Generic.List[string]
$md.Add("# Agent Codex Regression Report") | Out-Null
$md.Add("") | Out-Null
$md.Add("- Run: ``$RunId``") | Out-Null
$md.Add("- Root: ``$Root``") | Out-Null
$md.Add("- Passes: $($Passes.Count)") | Out-Null
$md.Add("- Warnings: $($Warnings.Count)") | Out-Null
$md.Add("- Failures: $($Failures.Count)") | Out-Null
$md.Add("") | Out-Null
$md.Add("## Levels") | Out-Null
$md.Add("") | Out-Null
$md.Add("| Level | Status | Failures | Warnings |") | Out-Null
$md.Add("|---|---|---:|---:|") | Out-Null
foreach ($level in $LevelResults) {
    $md.Add("| $($level.level) | $($level.status) | $($level.failures) | $($level.warnings) |") | Out-Null
}
if ($Failures.Count -gt 0) {
    $md.Add("") | Out-Null
    $md.Add("## Failures") | Out-Null
    foreach ($failure in $Failures) { $md.Add("- $failure") | Out-Null }
}
if ($Warnings.Count -gt 0) {
    $md.Add("") | Out-Null
    $md.Add("## Warnings") | Out-Null
    foreach ($warning in $Warnings) { $md.Add("- $warning") | Out-Null }
}
$md -join "`n" | Set-Content -LiteralPath $mdPath -Encoding UTF8

Write-Host ""
Write-Host "JSON report: $jsonPath"
Write-Host "MD report:   $mdPath"
Write-Host "Passes:      $($Passes.Count)"
Write-Host "Warnings:    $($Warnings.Count)"
Write-Host "Failures:    $($Failures.Count)"

if ($Failures.Count -gt 0) { exit 1 }
if ($Strict -and $Warnings.Count -gt 0) { exit 1 }
exit 0
