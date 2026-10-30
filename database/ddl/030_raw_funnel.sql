-- Raw Olist Marketing Funnel (Kaggle olistbr/marketing-funnel-olist). Verbatim text columns with the
-- exact source headers + load metadata. Full snapshots per file. Generated from
-- ingestion/sources/funnel.py contracts; keep in sync (pytest checks it).

create table if not exists raw.olist_marketing_qualified_leads (
    mql_id text not null,
    first_contact_date text,
    landing_page_id text,
    origin text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_marketing_qualified_leads__nk on raw.olist_marketing_qualified_leads (mql_id);

create table if not exists raw.olist_closed_deals (
    mql_id text not null,
    seller_id text,
    sdr_id text,
    sr_id text,
    won_date text,
    business_segment text,
    lead_type text,
    lead_behaviour_profile text,
    has_company text,
    has_gtin text,
    average_stock text,
    business_type text,
    declared_product_catalog_size text,
    declared_monthly_revenue text,
    _ingested_at timestamptz not null default now(),
    _source_file text not null,
    _batch_id uuid not null,
    _row_hash char(64) not null
);
create index if not exists ix_olist_closed_deals__nk on raw.olist_closed_deals (mql_id);
