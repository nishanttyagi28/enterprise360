# Shared helpers for the Windows (PowerShell 5.1+) scripts. Dot-source: . "$PSScriptRoot\_common.ps1"
$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$VenvPython = Join-Path $RepoRoot '.venv\Scripts\python.exe'

function Invoke-Step {
    param([string]$Name, [scriptblock]$Action)
    Write-Host "==> $Name" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) { throw "Step failed ($LASTEXITCODE): $Name" }
}

function Import-DotEnv {
    # Loads KEY=VALUE lines from .env into this process (needed for psql; python reads .env itself).
    $envFile = Join-Path $RepoRoot '.env'
    if (-not (Test-Path $envFile)) { throw ".env not found. Copy .env.example to .env and set POSTGRES_PASSWORD." }
    Get-Content -LiteralPath $envFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$' -and $_ -notmatch '^\s*#') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"').Trim("'"), 'Process')
        }
    }
}
