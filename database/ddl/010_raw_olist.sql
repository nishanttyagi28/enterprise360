-- Raw Olist landing tables: verbatim text columns (exact source names, typos kept) + load metadata.
-- Permissive by design: typing/uniqueness enforced in dbt so a bad file lands and is diagnosable.
-- NOT NULL only on natural-key columns (a row without its key is unusable anywhere downstream).
-- Generated from ingestion/sources/olist.py contracts; keep the two in sync (pytest checks it).

create table if not exists raw.olist_customers (
    customer_id text not null,
    customer_unique_id text,
    customer_zip_code_prefix text,
    customer_city text,
    customer_state text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_customers__nk on raw.olist_customers (customer_id);

create table if not exists raw.olist_geolocation (
    geolocation_zip_code_prefix text not null,
    geolocation_lat text,
    geolocation_lng text,
    geolocation_city text,
    geolocation_state text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_geolocation__nk on raw.olist_geolocation (geolocation_zip_code_prefix);

create table if not exists raw.olist_order_items (
    order_id text not null,
    order_item_id text not null,
    product_id text,
    seller_id text,
    shipping_limit_date text,
    price text,
    freight_value text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_order_items__nk on raw.olist_order_items (order_id, order_item_id);

create table if not exists raw.olist_order_payments (
    order_id text not null,
    payment_sequential text not null,
    payment_type text,
    payment_installments text,
    payment_value text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_order_payments__nk on raw.olist_order_payments (order_id, payment_sequential);

create table if not exists raw.olist_order_reviews (
    review_id text not null,
    order_id text not null,
    review_score text,
    review_comment_title text,
    review_comment_message text,
    review_creation_date text,
    review_answer_timestamp text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_order_reviews__nk on raw.olist_order_reviews (review_id, order_id);

create table if not exists raw.olist_orders (
    order_id text not null,
    customer_id text,
    order_status text,
    order_purchase_timestamp text,
    order_approved_at text,
    order_delivered_carrier_date text,
    order_delivered_customer_date text,
    order_estimated_delivery_date text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_orders__nk on raw.olist_orders (order_id);

create table if not exists raw.olist_products (
    product_id text not null,
    product_category_name text,
    product_name_lenght text,
    product_description_lenght text,
    product_photos_qty text,
    product_weight_g text,
    product_length_cm text,
    product_height_cm text,
    product_width_cm text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_products__nk on raw.olist_products (product_id);

create table if not exists raw.olist_sellers (
    seller_id text not null,
    seller_zip_code_prefix text,
    seller_city text,
    seller_state text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_sellers__nk on raw.olist_sellers (seller_id);

create table if not exists raw.olist_product_category_name_translation (
    product_category_name text not null,
    product_category_name_english text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_product_category_name_translation__nk on raw.olist_product_category_name_translation (product_category_name);
