{{ config(
    materialized='incremental',
    unique_key=['order_id', 'payment_sequential'],
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns'
) }}
-- Grain: payment (order_id, payment_sequential). Source of KPI_PAYMENT_VALUE.
-- Never joined to fct_order_items; compare at order grain only (fct_orders). Incremental rationale
-- as in fct_order_items.
select
    {{ dbt_utils.generate_surrogate_key(['p.order_id', 'p.payment_sequential']) }} as payment_sk,
    {{ dbt_utils.generate_surrogate_key(['p.order_id']) }}                         as order_sk,
    p.order_id,
    p.payment_sequential,
    {{ date_key('o.purchased_at') }}                                               as purchase_date_key,
    p.payment_type,
    p.payment_installments,
    p.payment_value,
    p._ingested_at                                                                 as _loaded_at
from {{ ref('stg_olist__order_payments') }} p
inner join {{ ref('stg_olist__orders') }} o on o.order_id = p.order_id
{% if is_incremental() %}
where p._ingested_at > (select coalesce(max(_loaded_at), '-infinity'::timestamptz) from {{ this }})
{% endif %}
