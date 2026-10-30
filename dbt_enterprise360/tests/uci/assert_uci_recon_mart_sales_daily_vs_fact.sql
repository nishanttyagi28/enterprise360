{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
-- KPI_UCI_GROSS_SALES: mart == fact (exact)
select * from (select sum(gross_product_sales) m from {{ ref('uci_mart_sales_daily') }}) a,
 (select sum(line_value) f from {{ ref('uci_fct_invoice_lines') }} where line_type='product' and not is_cancellation and quantity>0 and unit_price>0) b where a.m<>b.f
