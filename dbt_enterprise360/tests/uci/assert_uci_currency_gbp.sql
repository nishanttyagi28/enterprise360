{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
select currency from {{ ref('uci_fct_invoice_lines') }} where currency <> 'GBP' limit 1
