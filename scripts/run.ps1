<#
.SYNOPSIS  Ingest (Olist / UCI / Marketing Funnel) -> dbt freshness -> ONE dbt build (models + tests + DQ log) -> forecast. Optionally pytest/lint, MIS export.
.DESCRIPTION
  -Domain all (default) ingests olist, uci and funnel independently: if one domain's ingestion fails the other
  still loads, dbt build still runs, and the script exits non-zero at the end naming the failed domain.
.EXAMPLE   .\scripts\run.ps1                              # both domains: data\raw\olist + data\raw\uci_online_retail_ii
.EXAMPLE   .\scripts\run.ps1 -Domain uci                  # UCI only (dbt build still builds everything)
.EXAMPLE   .\scripts\run.ps1 -Domain funnel               # Marketing Funnel only (data\raw\olist_marketing_funnel)
.EXAMPLE   .\scripts\run.ps1 -SourceDir tests\fixtures\olist -UciSourceDir tests\fixtures\uci
.EXAMPLE   .\scripts\run.ps1 -FullRefresh -Test           # rebuild incrementals, then pytest + ruff + mypy
.EXAMPLE   .\scripts\run.ps1 -Prefect                     # same pipeline as a Prefect flow
.EXAMPLE   .\scripts\run.ps1 -Export                      # ... then reports\enterprise360_mis_YYYYMMDD.xlsx
#>
param(
    [ValidateSet('olist', 'uci', 'funnel', 'all')]
    [string]$Domain = 'all',
    [string]$SourceDir,       # Olist folder override (default E360_OLIST_DIR / data\raw\olist)
    [string]$UciSourceDir,    # UCI folder override (default E360_UCI_DIR / data\raw\uci_online_retail_ii)
    [string]$FunnelSourceDir, # Funnel folder override (default E360_FUNNEL_DIR / data\raw\olist_marketing_funnel)
    [switch]$Force,
    [switch]$FullRefresh,
    [switch]$Test,
    [switch]$Prefect,
    [switch]$SkipForecast,    # skip python -m analytics.forecast after dbt build
    [switch]$Export           # write reports\enterprise360_mis_YYYYMMDD.xlsx at the end
)
. "$PSScriptRoot\_common.ps1"
Set-Location $RepoRoot
if (-not (Test-Path $VenvPython)) { throw 'Run .\scripts\setup.ps1 first.' }

$domains = if ($Domain -eq 'all') { @('olist', 'uci', 'funnel') } else { @($Domain) }
$dirs = @{ olist = $SourceDir; uci = $UciSourceDir; funnel = $FunnelSourceDir }
$failed = @()

if ($Prefect) {
    $flowArgs = @('--domain', $Domain)
    if ($SourceDir) { $flowArgs += @('--source-dir', $SourceDir) }
    if ($UciSourceDir) { $flowArgs += @('--uci-source-dir', $UciSourceDir) }
    if ($FunnelSourceDir) { $flowArgs += @('--funnel-source-dir', $FunnelSourceDir) }
    if ($Force) { $flowArgs += '--force' }
    if ($FullRefresh) { $flowArgs += '--full-refresh' }
    if ($SkipForecast) { $flowArgs += '--skip-forecast' }
    Invoke-Step 'Prefect flow olist-pipeline' { & $VenvPython -m orchestration.flow @flowArgs }
} else {
    Invoke-Step 'Apply DDL' { & $VenvPython -m ingestion init-db }
    foreach ($d in $domains) {
        $ingestArgs = @($d)
        if ($dirs[$d]) { $ingestArgs += @('--source-dir', $dirs[$d]) }
        if ($Force) { $ingestArgs += '--force' }
        try {
            Invoke-Step "Ingest $d" { & $VenvPython -m ingestion @ingestArgs }
        } catch {
            Write-Warning "Ingest $d failed: $($_.Exception.Message). Continuing with the other domain(s)."
            $failed += $d
        }
    }
    Invoke-Step 'dbt deps' { & $VenvPython -m orchestration.dbt_runner deps }
    Invoke-Step 'dbt source freshness' { & $VenvPython -m orchestration.dbt_runner source freshness }
    $buildArgs = @('build')
    if ($FullRefresh) { $buildArgs += '--full-refresh' }
    Invoke-Step 'dbt build' { & $VenvPython -m orchestration.dbt_runner @buildArgs }
    if (-not $SkipForecast) {
        # Reads marts.mart_business_overview_monthly, writes analytics.forecast_*, rebuilds marts.mart_gmv_*
        Invoke-Step 'Forecast + anomalies' { & $VenvPython -m analytics.forecast }
    }
}

if ($Export) {
    Invoke-Step 'MIS Excel export' { & $VenvPython -m reporting.export_mis }
}

if ($Test) {
    Invoke-Step 'pytest' { & $VenvPython -m pytest }
    Invoke-Step 'ruff' { & $VenvPython -m ruff check ingestion orchestration analytics reporting tests }
    Invoke-Step 'mypy' { & $VenvPython -m mypy }
}
if ($failed.Count -gt 0) { throw "Ingestion failed for: $($failed -join ', ') (dbt build ran on the rest)." }
Write-Host 'Done. DQ score: SELECT * FROM core.dq_results WHERE is_latest_run;' -ForegroundColor Green
