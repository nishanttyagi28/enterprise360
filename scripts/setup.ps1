<#
.SYNOPSIS  One-time setup: venv (Python 3.12), dependencies, .env, optional role/DB creation, DDL.
.EXAMPLE   .\scripts\setup.ps1                 # DB enterprise360 / role e360_app already exist (laptop)
#   -CreateTestDatabase: create E360_TEST_DB (default enterprise360_test) for pytest integration tests.
.EXAMPLE   .\scripts\setup.ps1 -CreateTestDatabase
.EXAMPLE   .\scripts\setup.ps1 -CreateDatabase # also create role + DB as POSTGRES_ADMIN_USER via psql
#>
param(
    [switch]$CreateDatabase,
    [switch]$CreateTestDatabase,
    [string]$PsqlPath = 'C:\Program Files\PostgreSQL\16\bin\psql.exe'
)
. "$PSScriptRoot\_common.ps1"
Set-Location $RepoRoot

if (-not (Test-Path $VenvPython)) {
    Invoke-Step 'Create .venv with Python 3.12' { py -3.12 -m venv .venv }
}
Invoke-Step 'Upgrade pip' { & $VenvPython -m pip install --upgrade pip }
Invoke-Step 'Install enterprise360 (+dev)' { & $VenvPython -m pip install -e '.[dev]' }

if (-not (Test-Path (Join-Path $RepoRoot '.env'))) {
    Copy-Item (Join-Path $RepoRoot '.env.example') (Join-Path $RepoRoot '.env')
    Write-Warning '.env created from .env.example - set POSTGRES_PASSWORD, then re-run this script.'
    exit 1
}
Import-DotEnv

if ($CreateDatabase) {
    if (-not (Test-Path $PsqlPath)) { throw "psql not found at $PsqlPath (use -PsqlPath)" }
    $admin = if ($env:POSTGRES_ADMIN_USER) { $env:POSTGRES_ADMIN_USER } else { 'postgres' }
    $pw = $env:POSTGRES_PASSWORD.Replace("'", "''")
    $sqlRole = "DO `$`$BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$($env:POSTGRES_USER)') THEN CREATE ROLE $($env:POSTGRES_USER) LOGIN PASSWORD '$pw'; END IF; END`$`$;"
    Invoke-Step "Create role $($env:POSTGRES_USER) (prompts for $admin password)" {
        & $PsqlPath -h $env:POSTGRES_HOST -p $env:POSTGRES_PORT -U $admin -d postgres -v ON_ERROR_STOP=1 -c $sqlRole
    }
    $exists = & $PsqlPath -h $env:POSTGRES_HOST -p $env:POSTGRES_PORT -U $admin -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '$($env:POSTGRES_DB)'"
    if ($exists -ne '1') {
        Invoke-Step "Create database $($env:POSTGRES_DB)" {
            & $PsqlPath -h $env:POSTGRES_HOST -p $env:POSTGRES_PORT -U $admin -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE $($env:POSTGRES_DB) OWNER $($env:POSTGRES_USER) ENCODING 'UTF8'"
        }
    }
} else {
    Write-Host "Skipping DB creation (expects $($env:POSTGRES_DB) owned by $($env:POSTGRES_USER)). Use -CreateDatabase to create." -ForegroundColor DarkGray
}

if ($CreateTestDatabase) {
    if (-not (Test-Path $PsqlPath)) { throw "psql not found at $PsqlPath (use -PsqlPath)" }
    $testDb = if ($env:E360_TEST_DB) { $env:E360_TEST_DB } else { 'enterprise360_test' }
    if ($testDb -eq $env:POSTGRES_DB) { throw "E360_TEST_DB must differ from POSTGRES_DB" }
    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    $exists = & $PsqlPath -h $env:POSTGRES_HOST -p $env:POSTGRES_PORT -U $env:POSTGRES_USER -d $env:POSTGRES_DB -tAc "SELECT 1 FROM pg_database WHERE datname = '$testDb'"
    if ($exists -ne '1') {
        # Requires CREATEDB on POSTGRES_USER. If missing, a superuser runs once:
        #   psql -U postgres -c "ALTER ROLE e360_app CREATEDB;"
        #   (or) psql -U postgres -c "CREATE DATABASE enterprise360_test OWNER e360_app;"
        Invoke-Step "Create test database $testDb" {
            & $PsqlPath -h $env:POSTGRES_HOST -p $env:POSTGRES_PORT -U $env:POSTGRES_USER -d $env:POSTGRES_DB -v ON_ERROR_STOP=1 -c "CREATE DATABASE $testDb OWNER $($env:POSTGRES_USER) ENCODING 'UTF8'"
        }
    }
    Remove-Item Env:PGPASSWORD
}

Invoke-Step 'Apply DDL (schemas, raw tables, audit)' { & $VenvPython -m ingestion init-db }
Invoke-Step 'dbt deps' { & $VenvPython -m orchestration.dbt_runner deps }
Invoke-Step 'dbt debug (connection check)' { & $VenvPython -m orchestration.dbt_runner debug }
Write-Host 'Setup complete. Next: .\scripts\run.ps1' -ForegroundColor Green
