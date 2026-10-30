# dbt tests (KPI & Quality)
Names verified against DE's models on 2026-10-30 (CONFIRMED). New DE models used/relevant: int_olist__zip_prefix_centroid, int_olist__order_items_aggregated, int_olist__order_payments_aggregated, int_olist__order_items_enriched, int_olist__month_coverage; dim_date flags is_complete_month / is_low_volume_month / is_reporting_month.
- generic/: `grain_unique(columns)`, `row_count_matches(compare_model, key)` — attach in model yml.
- assert_grain_*: PK/grain per fact & dim. assert_recon_*: fact vs staging totals (tolerance 0). 
- assert_payments_vs_items_freight: WARN with categorised known exceptions. assert_no_fanout_*: join row preservation.

- Payments check compares in numeric(12,2); 1,076 WARN rows expected (772/264/39/1). kpi_id mapping via seeds/dq_check_config.csv.
