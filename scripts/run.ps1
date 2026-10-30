<#
.SYNOPSIS  Ingest Olist -> dbt freshness -> dbt build (models + tests + DQ log). Optionally pytest/lint.
.EXAMPLE   .\scripts\run.ps1                       # real data from E360_OLIST_DIR (data\raw\olist)
.EXAMPLE   .\scripts\run.ps1 -SourceDir tests\fixtures\olist
.EXAMPLE   .\scripts\run.ps1 -FullRefresh -Test    # rebuild incrementals, then pytest + ruff + mypy
.EXAMPLE   .\scripts\run.ps1 -Prefect              # same pipeline as a Prefect flow
#>
param(
    [string]$SourceDir,
    [switch]$Force,
    [switch]$FullRefresh,
    [switch]$Test,
    [switch]$Prefect
)
. "$PSScriptRoot\_common.ps1"
Set-Location $RepoRoot
if (-not (Test-Path $VenvPython)) { throw 'Run .\scripts\setup.ps1 first.' }

if ($Prefect) {
    $flowArgs = @()
    if ($SourceDir) { $flowArgs += @('--source-dir', $SourceDir) }
    if ($Force) { $flowArgs += '--force' }
    if ($FullRefresh) { $flowArgs += '--full-refresh' }
    Invoke-Step 'Prefect flow olist-pipeline' { & $VenvPython -m orchestration.flow @flowArgs }
} else {
    $ingestArgs = @('olist')
    if ($SourceDir) { $ingestArgs += @('--source-dir', $SourceDir) }
    if ($Force) { $ingestArgs += '--force' }
    Invoke-Step 'Apply DDL' { & $VenvPython -m ingestion init-db }
    Invoke-Step 'Ingest Olist' { & $VenvPython -m ingestion @ingestArgs }
    Invoke-Step 'dbt deps' { & $VenvPython -m orchestration.dbt_runner deps }
    Invoke-Step 'dbt source freshness' { & $VenvPython -m orchestration.dbt_runner source freshness }
    $buildArgs = @('build')
    if ($FullRefresh) { $buildArgs += '--full-refresh' }
    Invoke-Step 'dbt build' { & $VenvPython -m orchestration.dbt_runner @buildArgs }
}

if ($Test) {
    Invoke-Step 'pytest' { & $VenvPython -m pytest }
    Invoke-Step 'ruff' { & $VenvPython -m ruff check ingestion orchestration tests }
    Invoke-Step 'mypy' { & $VenvPython -m mypy }
}
Write-Host 'Done. DQ score: SELECT * FROM core.dq_results WHERE is_latest_run;' -ForegroundColor Green
