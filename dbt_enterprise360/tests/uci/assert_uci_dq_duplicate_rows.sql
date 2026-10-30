{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
{{ config(severity='warn') }}
-- exact duplicate business rows remaining after staging dedup (plan D1)
select invoice, stock_code, quantity, invoice_ts, unit_price, customer_id, count(*) from {{ ref('uci_fct_invoice_lines') }}
group by 1,2,3,4,5,6 having count(*) > 1
