{{ config(materialized='view') }}
-- core.dq_results: BI-facing DQ history, one row per run_id x check_id (appended every dbt run by
-- the on-run-end hook). A view over the persistent log so dbt rebuilding it never loses history.
-- DQ score (KPI_DQ_SCORE) for a run = sum(weight where status='pass') / sum(weight).
select
    run_id,
    run_at,
    check_id,
    check_name,
    layer,
    model_name,
    kpi_id,
    severity,
    weight,
    status,
    failing_rows,
    source_value,
    mart_value,
    variance,
    test_type,
    dbt_status,
    execution_seconds,
    run_at = max(run_at) over () as is_latest_run
from {{ source('dq', 'dq_results_log') }}
