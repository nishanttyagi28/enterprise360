{{ config(severity='warn', warn_if='>0', error_if='>' ~ var('payment_mismatch_error_threshold', 1000000)) }}
-- Per order |sum(payment_value) - sum(item_price+freight_value)| > 0.01 BRL.
-- WARN, not error: known exceptions = orders with payments but no items, vouchers,
-- installment interest/rounding. Each row is categorised; counts land in dq_results.
-- Aggregates each side BEFORE joining (no payments x items fan-out).
with p as (select order_id, sum(payment_value) pay from {{ ref('fct_payments') }} group by 1),
     i as (select order_id, sum(item_price + freight_value) itm from {{ ref('fct_order_items') }} group by 1)
select coalesce(p.order_id, i.order_id) order_id, p.pay, i.itm, coalesce(p.pay,0)-coalesce(i.itm,0) diff,
  case when i.order_id is null then 'payment_without_items'
       when p.order_id is null then 'items_without_payment'
       when p.pay > i.itm then 'overpaid (installment interest?)'
       else 'underpaid (voucher/discount?)' end as exception_category
from p full outer join i on p.order_id = i.order_id
where abs(coalesce(p.pay,0)-coalesce(i.itm,0)) > 0.01
