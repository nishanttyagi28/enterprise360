# Data lineage — Olist slice and UCI Online Retail II
Generated from the dbt DAG in `dbt_enterprise360/` (regenerate the interactive version with
`python -m orchestration.dbt_runner docs generate` then `... docs serve`). Power BI reads `core` and `marts`.

```mermaid
flowchart LR
  subgraph files[data/raw/olist CSVs]
    F1[orders]:::f; F2[customers]:::f; F3[order_items]:::f; F4[order_payments]:::f; F5[order_reviews]:::f
    F6[products]:::f; F7[category_translation]:::f; F8[sellers]:::f; F9[geolocation]:::f
  end
  subgraph raw[raw - python -m ingestion]
    R1[olist_orders]; R2[olist_customers]; R3[olist_order_items]; R4[olist_order_payments]; R5[olist_order_reviews]
    R6[olist_products]; R7[olist_product_category_name_translation]; R8[olist_sellers]; R9[olist_geolocation]; RA[_load_audit]
  end
  subgraph stg[staging - views]
    S1[stg_olist__orders]; S2[stg_olist__customers]; S3[stg_olist__order_items]; S4[stg_olist__order_payments]
    S5[stg_olist__order_reviews]; S6[stg_olist__products]; S7[stg_olist__category_translation]; S8[stg_olist__sellers]; S9[stg_olist__geolocation]
  end
  subgraph int[intermediate]
    I1[int_olist__customer_order_map]; I2[int_olist__zip_prefix_centroid]; I3[int_olist__order_items_aggregated]
    I4[int_olist__order_payments_aggregated]; I5[int_olist__order_review_latest]; I6[int_olist__order_items_enriched]; I7[int_olist__month_coverage]
  end
  subgraph core[core - star schema]
    D1[dim_date]; D2[dim_customer]; D3[dim_product]; D4[dim_seller]; D5[dim_geography]
    C1[fct_orders]; C2[fct_order_items]; C3[fct_payments]; C4[fct_reviews]; C5[fct_deliveries]
  end
  subgraph marts[marts]
    M1[mart_sales_daily]; M2[mart_sales_by_seller_monthly]; M3[mart_sales_by_category_monthly]
    M4[mart_operations_delivery_performance]; M5[mart_business_overview_monthly]; M6[mart_customer_cohorts]
  end
  subgraph dq[data quality]
    Q1[core.dq_reconciliation]; Q2[(dq.dq_results_log)]; Q3[core.dq_results]; Q4[core.dq_run_summary]; SEED[seed dq_check_config]
  end
  F1-->R1; F2-->R2; F3-->R3; F4-->R4; F5-->R5; F6-->R6; F7-->R7; F8-->R8; F9-->R9
  R1-->S1; R2-->S2; R3-->S3; R4-->S4; R5-->S5; R6-->S6; R7-->S7; R8-->S8; R9-->S9
  S2-->I1; S9-->I2; S3-->I3; S4-->I4; S5-->I5; S3-->I6; S1-->I6; S1-->I7
  I7-->D1; I1-->D2; S1-->D2; S6-->D3; S7-->D3; S8-->D4; I2-->D5; S2-->D5; S8-->D5
  S1-->C1; I1-->C1; I3-->C1; I4-->C1; I5-->C1
  I6-->C2; S4-->C3; S1-->C3; S5-->C4; I5-->C4; S1-->C5; I1-->C5
  C1-->M1; C2-->M1; C3-->M1; D1-->M1
  C2-->M2; D4-->M2; C2-->M3; D3-->M3; C5-->M4; D5-->M4
  C1-->M5; C2-->M5; C3-->M5; C5-->M5; D2-->M5; I7-->M5; C1-->M6; D2-->M6
  R1-->Q1; S1-->Q1; S3-->Q1; S4-->Q1; C1-->Q1; C2-->Q1; C3-->Q1; M1-->Q1
  Q1-. on-run-end hook .->Q2; SEED-.->Q2; Q2-->Q3-->Q4
  S8-->SNAP[snapshots.snap_olist__sellers]
  classDef f fill:#1b2a41,color:#cfe8ff
```

Notes
- Payments and order lines meet only at order grain (`int_*_aggregated` → `fct_orders`); never line × payment.
- Raw geolocation reaches the model only through the per-zip-prefix centroid.
- `dq.dq_results_log` is created by the on-run-start hook and appended by on-run-end (every dbt run, incl. warns).

## UCI Online Retail II (independent; no edges to Olist except shared DQ objects)
```mermaid
flowchart LR
  U1[online_retail_II_Year_2009-2010.csv]:::f --> UR[raw.uci_online_retail_ii_lines]
  U2[online_retail_II_Year_2010-2011.csv]:::f --> UR
  UR --> SA[stg_uci__invoice_lines_all<br/>dedup flags] --> SL[stg_uci__invoice_lines]
  SA --> DS[int_uci__dedup_stats]
  SL --> IC[int_uci__invoice_lines_classified]
  SEEDU[seed uci_stockcode_class] --> IC
  SL --> PD[int_uci__product_descriptions]
  IC --> FL[uci_fct_invoice_lines] --> FI[uci_fct_invoices]
  FL --> DP[uci_dim_product]; PD --> DP
  FI --> DC[uci_dim_customer]; SL --> DK[uci_dim_country]
  FI --> MC[int_uci__month_coverage] --> DD[uci_dim_date]
  FI --> MS[uci_mart_sales_daily]; DD --> MS
  FL --> MP[uci_mart_product_monthly]; DP --> MP
  FI --> MK[uci_mart_country_monthly]
  FI --> MH[uci_mart_customer_cohorts]; DC --> MH
  FI --> MR[uci_mart_customer_rfm]
  DS --> REC[core.dq_reconciliation]; FL --> REC; MS --> REC; MP --> REC
  classDef f fill:#1b2a41,color:#cfe8ff
```
