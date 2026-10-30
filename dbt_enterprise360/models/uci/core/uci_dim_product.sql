-- Grain: StockCode (original case; 'm' and 'M' are distinct codes in source). Description is SCD1 =
-- most frequent non-null text (ties -> most recently seen); full history in
-- int_uci__product_descriptions. Full SCD2 not justified: variants are relabels/typos without
-- effective dates. Price is a fact attribute (4,370 codes have several prices).
with lines as (select * from {{ ref('uci_fct_invoice_lines') }}),
best_desc as (
    select distinct on (stock_code) stock_code, description
    from {{ ref('int_uci__product_descriptions') }}
    order by stock_code, line_count desc, last_seen_at desc, description
),
types as (
    select distinct on (stock_code) stock_code, line_type
    from (select stock_code, line_type, count(*) n from lines group by 1, 2) x
    order by stock_code, n desc, line_type
),
agg as (
    select stock_code, min(invoice_ts) first_seen_at, max(invoice_ts) last_seen_at,
           count(distinct description) distinct_descriptions
    from lines group by 1
)
select
    {{ dbt_utils.generate_surrogate_key(['a.stock_code']) }} as uci_product_sk,
    a.stock_code,
    coalesce(d.description, 'unknown')                       as description,
    t.line_type                                              as primary_line_type,
    t.line_type = 'product'                                  as is_product,
    a.distinct_descriptions,
    a.first_seen_at,
    a.last_seen_at
from agg a
left join best_desc d using (stock_code)
left join types t using (stock_code)
