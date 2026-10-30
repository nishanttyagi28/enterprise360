-- grain: one row per (order_id, payment_sequential) in fct_payments. Returns duplicates.
select order_id, payment_sequential, count(*) as n from {{ ref('fct_payments') }} group by order_id, payment_sequential having count(*) > 1
