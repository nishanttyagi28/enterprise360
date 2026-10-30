-- Forecast / anomaly outputs written by `python -m analytics.forecast` (Python-owned, like raw).
-- Every run is kept (history, keyed by run_id); dbt marts marts.mart_gmv_* expose the latest successful run.
create schema if not exists analytics;

create table if not exists analytics.forecast_runs (
    run_id uuid primary key,
    generated_at timestamptz not null default now(),
    source_relation text not null,
    first_month date not null,
    last_month date not null,
    n_months integer not null,
    gmv_model text not null,
    orders_model text not null,
    gmv_selection_reason text,
    orders_selection_reason text,
    params jsonb not null,
    status text not null check (status in ('success'))
);

create table if not exists analytics.forecast_monthly (
    run_id uuid not null references analytics.forecast_runs (run_id),
    forecast_month date not null,
    split text not null check (split in ('train', 'validation', 'test', 'forecast')),
    training_cutoff date not null,
    horizon integer,
    actual_gmv numeric(14, 2),
    fitted_gmv numeric(14, 2),
    forecast_gmv numeric(14, 2),
    lower_gmv numeric(14, 2),
    upper_gmv numeric(14, 2),
    baseline_gmv numeric(14, 2),
    baseline_lower_gmv numeric(14, 2),
    baseline_upper_gmv numeric(14, 2),
    actual_orders numeric(12, 1),
    fitted_orders numeric(12, 1),
    forecast_orders numeric(12, 1),
    lower_orders numeric(12, 1),
    upper_orders numeric(12, 1),
    baseline_orders numeric(12, 1),
    baseline_lower_orders numeric(12, 1),
    baseline_upper_orders numeric(12, 1),
    interval_level numeric(4, 3) not null,
    interval_method text,
    primary key (run_id, forecast_month)
);

create table if not exists analytics.forecast_anomalies (
    run_id uuid not null references analytics.forecast_runs (run_id),
    anomaly_date date not null,
    gmv numeric(14, 2) not null,
    expected_gmv numeric(14, 2) not null,
    gmv_robust_z double precision not null,
    is_gmv_anomaly boolean not null,
    orders integer not null,
    expected_orders numeric(12, 1) not null,
    orders_robust_z double precision not null,
    is_orders_anomaly boolean not null,
    primary key (run_id, anomaly_date)
);

create table if not exists analytics.forecast_backtest (
    run_id uuid not null references analytics.forecast_runs (run_id),
    series text not null check (series in ('gmv', 'orders')),
    model text not null,
    split text not null,
    n_months integer not null,
    mae numeric(16, 4) not null,
    smape_pct numeric(8, 4) not null,
    mape_pct numeric(10, 4),
    is_selected_model boolean not null,
    primary key (run_id, series, model, split)
);

-- z can be huge when residual spread (MAD) is ~0; keep it unbounded (idempotent for early installs).
alter table analytics.forecast_anomalies alter column gmv_robust_z type double precision;
alter table analytics.forecast_anomalies alter column orders_robust_z type double precision;

-- v2 (rolling-origin CV selection, conformal intervals): idempotent upgrades of early installs.
alter table analytics.forecast_runs add column if not exists gmv_selection_reason text;
alter table analytics.forecast_runs add column if not exists orders_selection_reason text;
alter table analytics.forecast_monthly add column if not exists fitted_gmv numeric(14, 2);
alter table analytics.forecast_monthly add column if not exists fitted_orders numeric(12, 1);
alter table analytics.forecast_monthly add column if not exists interval_method text;
alter table analytics.forecast_monthly alter column forecast_gmv drop not null;
alter table analytics.forecast_monthly alter column forecast_orders drop not null;
alter table analytics.forecast_monthly alter column baseline_gmv drop not null;
alter table analytics.forecast_monthly alter column baseline_orders drop not null;
alter table analytics.forecast_backtest drop constraint if exists forecast_backtest_split_check;
alter table analytics.forecast_backtest drop constraint if exists forecast_backtest_split_check1;
do $$ begin
    alter table analytics.forecast_backtest
        add constraint forecast_backtest_split_ck check (split in ('cv', 'validation', 'test'));
exception when duplicate_object then null; end $$;
