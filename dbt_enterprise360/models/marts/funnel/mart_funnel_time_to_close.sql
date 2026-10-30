-- Grain: days-to-close bucket x origin (closed deals only). Distribution of lead -> deal duration.
-- share_of_origin_deals / cumulative share are within origin; for all origins sum deals per bucket.
with buckets(bucket_order, bucket, min_days, max_days) as (
    values (0, 'negative (anomaly)', -100000, -1), (1, '0-7', 0, 7), (2, '8-14', 8, 14), (3, '15-30', 15, 30),
           (4, '31-60', 31, 60), (5, '61-90', 61, 90), (6, '91-180', 91, 180), (7, '181+', 181, 100000)
),
deals as (
    select origin_sk, origin, days_to_close from {{ ref('fct_leads') }} where is_closed
),
agg as (
    select d.origin_sk, d.origin, b.bucket_order, b.bucket, b.min_days, b.max_days, count(*) as deals
    from deals d
    inner join buckets b on d.days_to_close between b.min_days and b.max_days
    group by 1, 2, 3, 4, 5, 6
)
select
    origin_sk,
    origin,
    bucket_order,
    bucket,
    greatest(min_days, -1)                                                       as bucket_min_days,
    case when max_days >= 100000 then null else max_days end                     as bucket_max_days,
    deals,
    round(deals::numeric / sum(deals) over (partition by origin_sk), 4)          as share_of_origin_deals,
    round(sum(deals) over (partition by origin_sk order by bucket_order)::numeric
          / sum(deals) over (partition by origin_sk), 4)                         as cumulative_share_of_origin_deals
from agg
