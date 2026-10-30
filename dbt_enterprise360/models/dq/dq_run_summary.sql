{{ config(materialized='view') }}
-- One row per dbt run: check counts by status and the strict weighted DQ score (KPI_DQ_SCORE).
-- Strict: only 'pass' earns weight; 'warn' and 'fail' earn 0. Warns are exposed separately.
select
    run_id,
    run_at,
    count(*)                                              as total_checks,
    count(*) filter (where status = 'pass')               as passed_checks,
    count(*) filter (where status = 'warn')               as warned_checks,
    count(*) filter (where status = 'fail')               as failed_checks,
    count(*) filter (where status = 'fail' and severity = 'block') as failed_block_checks,
    sum(weight)                                           as total_weight,
    coalesce(sum(weight) filter (where status = 'pass'), 0) as passed_weight,
    coalesce(sum(weight) filter (where status = 'warn'), 0) as warned_weight,
    round(coalesce(sum(weight) filter (where status = 'pass'), 0) / nullif(sum(weight), 0), 4) as dq_score,
    bool_and(is_latest_run)                               as is_latest_run
from {{ ref('dq_results') }}
group by run_id, run_at
