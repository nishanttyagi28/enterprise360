{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
{{ config(severity='warn') }}
-- Non-C lines with qty<0 must be classified stock_writeoff (3,457 on raw: price 0, no customer)
select invoice, stock_code from {{ ref('uci_fct_invoice_lines') }} where not is_cancellation and quantity < 0 and line_type <> 'stock_writeoff'
