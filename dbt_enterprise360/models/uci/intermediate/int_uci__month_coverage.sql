-- UCI month coverage (same rule/macro as Olist, own data): events = sales invoices (non-C).
-- `orders` column = sales invoices in the month.
{{ month_coverage(ref('uci_fct_invoices'), 'invoice_ts', where='not is_cancellation', ratio=var('uci_low_volume_ratio', 0.1)) }}
