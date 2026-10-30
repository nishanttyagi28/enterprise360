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
    c.execute("""create view l as select distinct f, Invoice inv, StockCode sc, Description, Quantity::int q,
      InvoiceDate::timestamp ts, Price::decimal(12,2) p, try_cast(try_cast("Customer ID" as double) as int) cid, Country
      from r where f='f2' or InvoiceDate::timestamp < '2010-12-01'""")
    return c


def test_header_contract(uci):
    assert [d[0] for d in uci.execute("describe r").fetchall()][:8] == COLS


def test_types_parse(uci):
    assert uci.execute("select count(*) from r where try_cast(Quantity as int) is null or try_cast(Price as decimal(12,2)) is null or try_cast(InvoiceDate as timestamp) is null").fetchone()[0] == 0


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
