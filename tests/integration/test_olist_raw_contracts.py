"""Source contracts that the dbt grain/recon tests rely on, checked on the REAL raw Olist CSVs."""
import pytest

pytestmark = pytest.mark.integration

GRAINS = {
    "orders": ["order_id"],
    "order_items": ["order_id", "order_item_id"],
    "order_payments": ["order_id", "payment_sequential"],
    "customers": ["customer_id"],
    "products": ["product_id"],
    "sellers": ["seller_id"],
}

@pytest.mark.parametrize("table,cols", GRAINS.items())
def test_source_grain_unique(duck, table, cols):
    c = ", ".join(cols)
    dups = duck.execute(f"select count(*) from (select {c} from {table} group by {c} having count(*)>1)").fetchone()[0]
    assert dups == 0, f"{table} duplicate {cols}: {dups}"

def test_review_id_not_unique_alone_but_pair_is(duck):
    pair = duck.execute("select count(*) from (select review_id, order_id from order_reviews group by 1,2 having count(*)>1)").fetchone()[0]
    assert pair == 0

def test_items_fk_orders(duck):
    orphans = duck.execute("select count(*) from order_items i left join orders o using(order_id) where o.order_id is null").fetchone()[0]
    assert orphans == 0

def test_customer_map_one_to_one(duck):
    n = duck.execute("select count(*) from (select customer_id from customers group by 1 having count(distinct customer_unique_id)>1)").fetchone()[0]
    assert n == 0

def test_order_status_domain(duck):
    vals = {r[0] for r in duck.execute("select distinct order_status from orders").fetchall()}
    assert vals <= {"delivered","shipped","canceled","unavailable","invoiced","processing","created","approved"}, vals

def test_payments_vs_items_freight_exceptions_categorised(duck):
    rows = duck.execute("""
      with p as (select order_id, sum(payment_value) pay from order_payments group by 1),
           i as (select order_id, sum(price+freight_value) itm from order_items group by 1)
      select case when i.order_id is null then 'payment_without_items'
                  when p.order_id is null then 'items_without_payment'
                  when p.pay>i.itm then 'overpaid' else 'underpaid' end cat, count(*)
      from p full join i using(order_id) where abs(coalesce(pay,0)-coalesce(itm,0))>0.01 group by 1""").fetchall()
    print("payment vs items+freight exceptions:", rows)
    assert all(cat in {"payment_without_items","items_without_payment","overpaid","underpaid"} for cat,_ in rows)

def test_no_fanout_geolocation_raw_join(duck):
    """Documents why raw geolocation must be aggregated first: raw join multiplies customers."""
    base = duck.execute("select count(*) from customers").fetchone()[0]
    joined = duck.execute("select count(*) from customers c left join geolocation g on c.customer_zip_code_prefix=g.geolocation_zip_code_prefix").fetchone()[0]
    agg = duck.execute("select count(*) from customers c left join (select distinct geolocation_zip_code_prefix z from geolocation) g on c.customer_zip_code_prefix=g.z").fetchone()[0]
    assert joined > base and agg == base
