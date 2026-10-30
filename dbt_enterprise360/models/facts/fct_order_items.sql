{{ config(
    materialized='incremental',
    unique_key=['order_id', 'order_item_id'],
    incremental_strategy='delete+insert',
    on_schema_change='append_new_columns'
) }}
-- Grain: order line (order_id, order_item_id); each line = 1 unit. Source of KPI_GMV, KPI_NET_GMV,
-- KPI_FREIGHT. Incremental on _ingested_at: raw is batch-replaced only when the file hash changes,
-- so unchanged files cost nothing and a changed file reprocesses exactly its rows. Lines deleted
-- upstream are not removed incrementally -> use --full-refresh after a source restatement
-- (assert_recon_fct_order_items_vs_staging fails loudly if that is ever needed).
-- Surrogate FKs are deterministic hashes of the business keys, so no dimension lookups are needed.
select
    {{ dbt_utils.generate_surrogate_key(['order_id', 'order_item_id']) }} as order_item_sk,
    {{ dbt_utils.generate_surrogate_key(['order_id']) }}                  as order_sk,
    order_id,
    order_item_id,
    {{ dbt_utils.generate_surrogate_key(['product_id']) }}               as product_sk,
    {{ dbt_utils.generate_surrogate_key(['seller_id']) }}                as seller_sk,
    product_id,
    seller_id,
    {{ date_key('purchased_at') }}                                       as purchase_date_key,
    purchased_at,
    order_status,
    is_canceled,
    shipping_limit_at,
    delivered_carrier_at,
    -- Seller handover SLA, per line against that line's own deadline. NULL when either side is
    -- missing (not handed over yet / canceled), so NULL never counts as late or on time.
    case when delivered_carrier_at is not null and shipping_limit_at is not null
         then delivered_carrier_at <= shipping_limit_at end              as is_handover_on_time,
    1::smallint                                                          as item_quantity,
    item_price,
    freight_value,
    (item_price + freight_value)::numeric(12, 2)                         as item_gross_value,
    _ingested_at                                                         as _loaded_at
from {{ ref('int_olist__order_items_enriched') }}
{% if is_incremental() %}
where _ingested_at > (select coalesce(max(_loaded_at), '-infinity'::timestamptz) from {{ this }})
{% endif %}
