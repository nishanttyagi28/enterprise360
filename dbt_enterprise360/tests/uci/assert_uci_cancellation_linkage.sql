{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
{{ config(severity='warn') }}
-- C invoices: quantity<=0 (1 known exception) and every C invoice flagged is_cancellation; non-C never flagged
select invoice, quantity, is_cancellation from {{ ref('uci_fct_invoice_lines') }}
where (invoice like 'C%') <> is_cancellation or (is_cancellation and quantity > 0)
