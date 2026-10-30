{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
{{ config(severity='warn') }}
-- price<=0 outside bad_debt/stock_writeoff
select invoice, stock_code, unit_price from {{ ref('uci_fct_invoice_lines') }} where unit_price <= 0 and line_type not in ('bad_debt','stock_writeoff')
