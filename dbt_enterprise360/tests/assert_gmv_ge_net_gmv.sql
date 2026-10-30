-- KPI_GMV >= KPI_NET_GMV per month (GMV is not revenue; net is a status filter only)
select date_trunc('month', o.purchased_at) m, sum(i.item_price) gmv,
       sum(case when o.order_status not in ('canceled','unavailable') then i.item_price else 0 end) net
from {{ ref('fct_order_items') }} i join {{ ref('fct_orders') }} o on i.order_id = o.order_id
group by 1 having sum(i.item_price) < sum(case when o.order_status not in ('canceled','unavailable') then i.item_price else 0 end)
