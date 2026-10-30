{{ config(enabled=var('uci_models_built', false)) }}
-- ASSUMPTION: uci_* models not built yet; names from docs/blueprint/uci-online-retail-plan.md. Confirm with DE.
select i.invoice from {{ ref('uci_fct_invoices') }} i join (select invoice, count(*) lines from {{ ref('uci_fct_invoice_lines') }} group by 1) l using (invoice) where i.line_count <> l.lines
