with src as (select * from {{ source('olist', 'olist_orders') }}),
deduped as ({{ dedupe('src', ['order_id']) }})
select
    trim(order_id)                                   as order_id,
    trim(customer_id)                                as customer_id,
    lower({{ clean_text('order_status') }})          as order_status,
    -- Brazil local time, no zone in source -> timestamp without time zone, never shifted (STTM 2.1)
    {{ to_ts('order_purchase_timestamp') }}          as purchased_at,
    {{ to_ts('order_approved_at') }}                 as approved_at,
    {{ to_ts('order_delivered_carrier_date') }}      as delivered_carrier_at,
    {{ to_ts('order_delivered_customer_date') }}     as delivered_customer_at,
    {{ to_ts('order_estimated_delivery_date') }}     as estimated_delivery_at,
    _ingested_at
from deduped
