import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OLIST_ZIP = ROOT / "data" / "raw" / "olist" / "brazilian-ecommerce.zip"

@pytest.fixture(scope="session")
def repo_root() -> Path:
    return ROOT

@pytest.fixture(scope="session")
def olist_dir(tmp_path_factory) -> Path:
    if not OLIST_ZIP.exists():
        pytest.skip(f"Olist raw zip not present at {OLIST_ZIP}")
    out = tmp_path_factory.mktemp("olist")
    zipfile.ZipFile(OLIST_ZIP).extractall(out)
    return out

@pytest.fixture(scope="session")
def duck(olist_dir):
    duckdb = pytest.importorskip("duckdb")
    con = duckdb.connect()
    for f in olist_dir.glob("*.csv"):
        name = f.stem.replace("olist_", "").replace("_dataset", "")
        con.execute(f"create view {name} as select * from read_csv_auto('{f}', header=true, all_varchar=false)")
    return con


@pytest.fixture(scope="session")
def test_db_name() -> str:
    """Disposable DB for destructive ingestion integration tests (Data Engineering)."""
    import os

    return os.environ.get("E360_TEST_DB", "enterprise360_test")
