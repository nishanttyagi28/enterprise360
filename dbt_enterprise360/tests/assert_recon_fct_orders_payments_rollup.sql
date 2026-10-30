-- Payment totals per order in fct_orders equal fct_payments (each payment counted exactly once).
with p as (select order_id, sum(payment_value) v, count(*) n from {{ ref('fct_payments') }} group by 1)
select o.order_id, o.payment_value_total, p.v
from {{ ref('fct_orders') }} o
full outer join p on p.order_id = o.order_id
where coalesce(o.payment_value_total, 0) <> coalesce(p.v, 0) or coalesce(o.payment_count, 0) <> coalesce(p.n, 0)
