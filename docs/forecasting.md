# Forecasting & anomalies — monthly Olist GMV and orders

Owner: Data Engineering · Code: `analytics/forecasting/` · Run: `python -m analytics.forecast`
(or `.\scripts\run.ps1`, which runs it after `dbt build`; `-SkipForecast` to skip).

## What is forecast
* **GMV** = sum of order-item **price** only (`marts.mart_business_overview_monthly.gmv`; excludes freight;
  includes canceled orders as in KPI_GMV). It is **not revenue**.
* **Orders** = orders purchased in the month.
* Training months: `is_complete_month AND is_reporting_month` only → **2017-01 … 2018-08 (20 months)**.
  Excluded: 2016-09/10/12 (sparse launch months) and the 2018-09/10 tail (16 and 4 orders).

## Method (simple and transparent on purpose)
| Step | Rule |
|---|---|
| Candidates | Holt's additive **damped** trend (ETS A,Ad,N) and simple exponential smoothing (ETS A,N,N), statsmodels `ETSModel` |
| Baseline | **Last-value naive**. Seasonal-naive needs ≥ 2 full years; we have 20 months → infeasible |
| Split | chronological: **train** 14 (2017-01..2018-02) · **validation** 3 (2018-03..05) · **test** 3 (2018-06..08) |
| Selection | **rolling-origin CV on train+validation only** (expanding window, origins from month 8, up to 6 steps ahead, never past 2018-05). Lowest mean CV sMAPE candidate is selected **only if it beats the baseline's CV sMAPE; otherwise the baseline is published**. `selected_model` + `selection_reason` are stored. The test window is never used for selection or tuning |
| Backtest | selected model refit on train+validation, scored on test; candidate and baseline metrics stored for cv, validation and test, whichever wins |
| Forecast | selected model refit on all 20 months; horizon 6 (3..6 allowed) |
| Intervals | `interval_method = conformal_abs_cv`: per-horizon split-conformal half-width = the ⌈(n+1)·0.95⌉/n empirical quantile of rolling-origin CV absolute errors (the max when n is small), non-decreasing in h. Validation/test rows use CV on months before their cutoff only; forecast rows use CV on all 20 months. Lower bound clipped at 0 for forecast rows |
| Metrics | MAE, sMAPE (%), MAPE (%) |
| Train rows | `fitted_gmv` / `fitted_orders` = in-sample one-step fit (params from train); `forecast_*` is null |
| Anomalies | expected = one-step **in-sample** fit of the selected model **with parameters estimated on all 20 months** (naive → previous month), so the flag is descriptive, not an out-of-sample test; robust z = \|r − median(r)\| / (1.4826 · MAD(r)); **anomaly iff z > 3.5** |

`training_cutoff` on each row is the last month the producing model saw; validation/test/forecast rows are
strictly after it (tested: `assert_forecast_no_train_test_overlap`).

## Outputs
Python writes one run per execution (history kept) to `analytics.forecast_runs`, `forecast_monthly`,
`forecast_anomalies`, `forecast_backtest` (DDL `database/ddl/040_analytics_forecast.sql`, dbt sources
`analytics.*`). dbt then exposes the **latest successful run** (Power BI reads these):

| Table | Grain | Key columns |
|---|---|---|
| `marts.mart_gmv_forecast` | forecast_month | split, training_cutoff, horizon, model, actual_gmv, forecast_gmv, lower_gmv, upper_gmv, baseline_gmv (+ baseline PI), orders_model, actual/forecast/lower/upper/baseline_orders, interval_level, is_anomaly, is_orders_anomaly, is_forecast, run_id, generated_at |
| `marts.mart_gmv_anomalies` | anomaly_date (month start) | gmv, expected_gmv, gmv_residual, gmv_robust_z, is_gmv_anomaly, orders, expected_orders, orders_robust_z, is_orders_anomaly, is_anomaly, z_threshold, model, run_id |
| `marts.mart_gmv_forecast_backtest` | series × model × split | n_months, mae, smape_pct, mape_pct, is_selected_model |

## Results on the real data (latest run, 2026-10-31 IST)
| Series | Selected (reason) | CV sMAPE model / naive | Test sMAPE model / naive | Test MAE model / naive |
|---|---|---|---|---|
| GMV | holt_damped (CV 16.80% < 21.21%) | 16.80% / 21.21% | **28.25% / 13.37%** | R$287k / R$125k |
| Orders | holt_damped (CV 17.73% < 22.16%) | 17.73% / 22.16% | **22.31% / 8.35%** | 1,589 / 549 |

* Following the rule (select on train+validation only) Holt damped wins CV, which is dominated by the 2017
  growth phase, but **loses to the naive baseline on the 2018-06..08 test** because GMV/orders plateaued from
  mid-2018. This is reported, not tuned away; KPI & Quality's warn test `assert_forecast_model_beats_baseline`
  flags it. Use the baseline columns next to the model.
* Conformal 95% intervals now contain all 3 test actuals for both series (the earlier analytic ETS intervals
  missed all 3).
* GMV forecast 2018-09..2019-02: R$0.94 M → R$1.03 M/month (95% ≈ R$0.62–1.26 M at h=1, widening to
  R$0.60–1.47 M). Orders: 6,814 → 7,492. Baseline: R$854,686 / 6,512 flat.
* Anomalies (z > 3.5): **orders 2017-11 (Black Friday, z ≈ 5.6)**; no GMV month exceeds 3.5 (2017-11 GMV z ≈ 2.8).

## Limits — read before using the numbers
* Only 20 usable months; no yearly seasonality can be estimated (Black Friday/Christmas are not modelled, so
  Nov forecasts will be low and the 2017-11 spike inflates the fitted trend).
* The test window shows a regime change (2018 plateau); with 3 test points metrics are noisy.
* Prediction intervals assume additive, homoscedastic errors and the model being right; treat them as
  indicative. The dataset ends 2018-10, so forecasts can never be validated against later actuals.
* The first months' one-step fits are initialisation-driven; anomaly z for 2017-01..03 is less reliable.
* Use the forecast as a planning reference next to the naive baseline, not as a target.
