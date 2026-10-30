{{ config(materialized='ephemeral') }}
-- The latest successful forecast run (0 rows before the first `python -m analytics.forecast`).
select run_id, generated_at, gmv_model, orders_model, gmv_selection_reason, orders_selection_reason, first_month, last_month, n_months
from {{ source('analytics', 'forecast_runs') }}
where status = 'success'
order by generated_at desc, run_id
limit 1
