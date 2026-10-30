-- Grain: identified customer (snapshot at day after the last invoice in the data). Inputs for
-- segmentation (P6). monetary = Net Sales (proxy) incl. that customer's cancellations/discounts.
with snap as (select (max(invoice_ts)::date + 1) as snapshot_date from {{ ref('uci_fct_invoices') }}),
per as (
    select customer_id,
           max(invoice_ts) filter (where not is_cancellation)  as last_purchase_ts,
           count(*) filter (where not is_cancellation)         as frequency,
           sum(net_sales_proxy_gbp)                            as monetary_net_sales_proxy_gbp
    from {{ ref('uci_fct_invoices') }}
    where has_customer
    group by 1
)
select
    p.customer_id,
    {{ dbt_utils.generate_surrogate_key(['p.customer_id']) }}   as uci_customer_sk,
    s.snapshot_date,
    s.snapshot_date - p.last_purchase_ts::date                  as recency_days,
    p.frequency,
    p.monetary_net_sales_proxy_gbp,
    ntile(5) over (order by s.snapshot_date - p.last_purchase_ts::date desc nulls first) as r_score,
    ntile(5) over (order by p.frequency)                        as f_score,
    ntile(5) over (order by p.monetary_net_sales_proxy_gbp)     as m_score,
    'GBP'::char(3)                                              as currency
from per p cross join snap s
