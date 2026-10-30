-- Payments rolled up to ORDER grain. Payments are NEVER joined to order lines (n x m fan-out);
-- they meet items only at order grain, here and in fct_orders.
select
    order_id,
    count(*)                                                   as payment_count,
    sum(payment_value)                                         as payment_value_total,
    max(payment_installments)                                  as max_installments,
    count(distinct payment_type)                               as distinct_payment_types,
    -- primary method = largest share of value; ties broken by sequence for determinism
    (array_agg(payment_type order by payment_value desc, payment_sequential))[1] as primary_payment_type,
    bool_or(payment_type = 'voucher')                          as used_voucher
from {{ ref('stg_olist__order_payments') }}
group by order_id
