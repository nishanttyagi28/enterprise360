-- Grain: series x model x split (latest run). Holdout metrics for the selected model and the naive baseline.
select
    b.series, b.model, b.split, b.n_months, b.mae, b.smape_pct, b.mape_pct, b.is_selected_model,
    b.run_id, r.generated_at
from {{ source('analytics', 'forecast_backtest') }} b
inner join {{ ref('int_latest_forecast_run') }} r on r.run_id = b.run_id
