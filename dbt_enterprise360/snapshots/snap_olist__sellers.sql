{% snapshot snap_olist__sellers %}
{# SCD2 candidate: a seller can relocate (zip/city/state). Olist ships one static snapshot, so
   today this holds one version per seller; it starts accruing history once refreshed files land.
   check strategy because the source carries no updated_at column. #}
{{ config(
    unique_key='seller_id',
    strategy='check',
    check_cols=['seller_zip_prefix', 'seller_city', 'seller_state'],
    invalidate_hard_deletes=True
) }}
select seller_id, seller_zip_prefix, seller_city, seller_state from {{ ref('stg_olist__sellers') }}
{% endsnapshot %}
