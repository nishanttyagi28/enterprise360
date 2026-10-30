"""UCI Online Retail II raw contracts (read-only over the CSVs; never touches any database)."""
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration
DIR = Path(__file__).resolve().parents[2] / "data" / "raw" / "uci_online_retail_ii"
F1, F2 = DIR / "online_retail_II_Year_2009-2010.csv", DIR / "online_retail_II_Year_2010-2011.csv"
COLS = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]


@pytest.fixture(scope="module")
def uci():
    if not (F1.exists() and F2.exists()):
        pytest.skip(f"UCI CSVs not present under {DIR}")
    duckdb = pytest.importorskip("duckdb")
    c = duckdb.connect()
    c.execute(f"""create view r as
      select *, 'f1' f from read_csv('{F1}', all_varchar=true) union all
      select *, 'f2' f from read_csv('{F2}', all_varchar=true)""")
    # plan §3: overlap rule by date window + exact dedupe within file
    # exact decimal only (prices carry 3 dp -> decimal(12,3), as DE's numeric(12,3)); Customer ID '13085.0' via decimal
    c.execute("""create view l as select distinct f, Invoice inv, StockCode sc, Description, Quantity::int q,
      InvoiceDate::timestamp ts, Price::decimal(12,3) p, try_cast("Customer ID"::decimal(18,1) as int) cid, Country
      from r where f='f2' or InvoiceDate::timestamp < (select min(InvoiceDate::timestamp) from r where f='f2')""")
    return c


def test_header_contract(uci):
    assert [d[0] for d in uci.execute("describe r").fetchall()][:8] == COLS


def test_types_parse(uci):
    assert uci.execute("select count(*) from r where try_cast(Quantity as int) is null or try_cast(Price as decimal(12,3)) is null or try_cast(InvoiceDate as timestamp) is null").fetchone()[0] == 0


def test_deduped_row_count(uci):
    assert uci.execute("select count(*) from l").fetchone()[0] == 1_033_036


def test_negative_qty_non_c_are_writeoffs(uci):
    bad = uci.execute("select count(*) from l where inv not like 'C%' and q<0 and (p<>0 or cid is not null)").fetchone()[0]
    assert bad == 0


def test_negative_price_only_bad_debt(uci):
    assert uci.execute("select count(*) from l where p<0 and not (inv like 'A%' and upper(sc)='B')").fetchone()[0] == 0


def test_cancellation_qty_sign(uci):
    # 1 known exception (plan §1)
    assert uci.execute("select count(*) from l where inv like 'C%' and q>=0").fetchone()[0] <= 1


def test_missing_customer_share_reported(uci):
    share = uci.execute("select avg(case when cid is null then 1.0 else 0 end) from l").fetchone()[0]
    print(f"UCI missing Customer ID share: {share:.4f}")
    assert 0 < share < 1


# DE seed uci_stockcode_class, matched on upper(StockCode); prefix rules ADJUST%, TEST%, GIFT_%.
NON_PRODUCT = ("(upper(sc) in ('POST','DOT','C2','M','D','S','BANK CHARGES','AMAZONFEE','CRUK','B') "
               "or upper(sc) like 'ADJUST%' or upper(sc) like 'TEST%' or upper(sc) like 'GIFT\\_%' escape '\\')")


def test_adjust_prefix_classified(uci):
    codes = {r[0] for r in uci.execute("select distinct upper(sc) from l where upper(sc) like 'ADJUST%'").fetchall()}
    assert "ADJUST" in codes and len(codes) > 1, codes  # e.g. ADJUST2 must match the prefix rule


def test_gross_product_sales_exact(uci):
    from decimal import Decimal
    v = uci.execute(f"""select sum(q*p) from l where not {NON_PRODUCT} and inv not like 'C%' and inv not like 'A%'
                        and p > 0 and q > 0""").fetchone()[0]
    assert v == Decimal("19643861.637")  # = uci_mart_sales_daily.gross_product_sales (displays 19,643,861.64)
