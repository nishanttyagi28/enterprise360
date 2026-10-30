"""Live-DB tests: COPY load, idempotency, incremental skip, audit, SQL/Python row-hash parity.

Runs against E360_PG_* (a disposable database, e.g. e360_fixture / the CI service). Skipped when
no server is reachable. Loads the fixture CSVs only.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest

from ingestion.config import Settings
from ingestion.loaders import LoadStatus, row_hash
from ingestion.pipeline import apply_ddl, connect, load_contract_files, load_file, load_source, run_olist
from ingestion.sources import OLIST_CONTRACTS, UCI_ONLINE_RETAIL_II, get_contract

pytestmark = pytest.mark.integration
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "olist"
UCI_FIXTURES = ROOT / "tests" / "fixtures" / "uci"


# These tests REPLACE raw tables with fixtures, so they run against a dedicated test database
# (E360_TEST_DB, default enterprise360_test; resolved in tests/conftest.py) and refuse the main one.


@pytest.fixture(scope="module")
def settings(test_db_name: str) -> Settings:
    main_db = Settings().pg_db
    if test_db_name in {main_db, "enterprise360"}:
        pytest.fail(f"E360_TEST_DB={test_db_name!r} is the main warehouse; refusing destructive tests")
    s = Settings().model_copy(update={"pg_db": test_db_name})
    try:
        psycopg.connect(s.conninfo, connect_timeout=3).close()
    except psycopg.OperationalError as exc:
        pytest.skip(f"PostgreSQL not reachable: {exc}")
    return s


@pytest.fixture()
def conn(settings: Settings) -> Iterator[psycopg.Connection]:
    with connect(settings) as c:
        apply_ddl(c, ROOT / "database" / "ddl")
        yield c


def _count(conn: psycopg.Connection, table: str) -> int:
    row = conn.execute(f"select count(*) from {table}").fetchone()
    assert row is not None
    return int(row[0])


def test_full_load_then_rerun_is_skipped(settings: Settings, conn: psycopg.Connection) -> None:
    first = run_olist(settings, source_dir=FIXTURES, force=True)
    assert all(r.status is LoadStatus.SUCCESS for r in first)
    counts = {c.table: _count(conn, c.qualified_table) for c in OLIST_CONTRACTS}
    assert counts["olist_order_reviews"] == 5  # multi-line quoted message parsed as one row
    second = run_olist(settings, source_dir=FIXTURES)
    assert all(r.status is LoadStatus.SKIPPED for r in second)
    assert counts == {c.table: _count(conn, c.qualified_table) for c in OLIST_CONTRACTS}


def test_forced_reload_replaces_not_appends(settings: Settings, conn: psycopg.Connection) -> None:
    contract = get_contract("olist_order_items")
    load_source(conn, contract, FIXTURES, force=True)
    before = _count(conn, contract.qualified_table)
    load_source(conn, contract, FIXTURES, force=True)
    assert _count(conn, contract.qualified_table) == before
    batches = conn.execute("select count(distinct _batch_id) from raw.olist_order_items").fetchone()
    assert batches == (1,)


def test_changed_file_is_reloaded(conn: psycopg.Connection, tmp_path: Path) -> None:
    contract = get_contract("olist_sellers")
    for c in OLIST_CONTRACTS:
        shutil.copy(FIXTURES / c.file_name, tmp_path / c.file_name)
    load_source(conn, contract, tmp_path, force=True)
    with (tmp_path / contract.file_name).open("a", encoding="utf-8", newline="") as fh:
        fh.write('"s0000000000000000000000000000009","04001","sao paulo","SP"\n')
    result = load_source(conn, contract, tmp_path)
    assert result.status is LoadStatus.SUCCESS and result.rows_loaded == 3
    load_source(conn, contract, FIXTURES, force=True)  # restore fixture state


def test_sql_row_hash_matches_python(conn: psycopg.Connection) -> None:
    contract = get_contract("olist_sellers")
    load_source(conn, contract, FIXTURES, force=True)
    cols = ", ".join(contract.columns)
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        rows = cur.execute(f"select {cols}, _row_hash from raw.olist_sellers").fetchall()
    for r in rows:
        assert r["_row_hash"] == row_hash({c: r[c] for c in contract.columns}, contract.columns)


def test_audit_records_runs(conn: psycopg.Connection) -> None:
    row = conn.execute(
        "select count(*) filter (where status='success'), count(*) filter (where status='running') "
        "from raw._load_audit"
    ).fetchone()
    assert row is not None and row[0] > 0 and row[1] == 0


def test_uci_files_load_independently_with_line_numbers(conn: psycopg.Connection, tmp_path: Path) -> None:
    contract = UCI_ONLINE_RETAIL_II
    results = load_contract_files(conn, contract, UCI_FIXTURES, force=True)
    assert [r.rows_loaded for r in results] == [6, 5]  # exact duplicate kept in raw (dropped in dbt)
    rows = conn.execute(
        'select _source_file, _source_line_no, "Invoice", "Customer ID" '
        "from raw.uci_online_retail_ii_lines order by 1, 2"
    ).fetchall()
    first = [r for r in rows if r[0].endswith("2009-2010.csv")]
    assert [r[1] for r in first] == [1, 2, 3, 4, 5, 6]
    assert first[0][2] == "489434" and first[4][3] is None  # COPY CSV: unquoted empty field -> NULL
    # reloading ONE changed file must not touch the other file's rows
    for name in contract.file_names:
        shutil.copy(UCI_FIXTURES / name, tmp_path / name)
    with (tmp_path / contract.file_names[1]).open("a", encoding="utf-8", newline="") as fh:
        fh.write("536368,22000,TEST ITEM,1,2011-02-01 10:00:00,1.00,17850.0,United Kingdom\n")
    second = load_contract_files(conn, contract, tmp_path)
    assert [r.status for r in second] == [LoadStatus.SKIPPED, LoadStatus.SUCCESS]
    counts = dict(
        conn.execute(
            "select _source_file, count(*) from raw.uci_online_retail_ii_lines group by 1"
        ).fetchall()
    )
    assert counts == {contract.file_names[0]: 6, contract.file_names[1]: 6}
    load_file(conn, contract, UCI_FIXTURES / contract.file_names[1], force=True)
