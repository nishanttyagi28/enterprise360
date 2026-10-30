"""Schema contracts vs fixtures, raw DDL and the header validator."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ingestion.exceptions import ContractViolationError, SourceFileMissingError
from ingestion.extractors import describe_file, read_header
from ingestion.sources import OLIST_CONTRACTS, SourceContract, get_contract
from ingestion.validators import validate_header

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "olist"


def test_nine_olist_contracts_with_unique_tables() -> None:
    assert len(OLIST_CONTRACTS) == 9
    assert len({c.table for c in OLIST_CONTRACTS}) == 9


def test_products_contract_keeps_source_typos() -> None:
    cols = get_contract("olist_products").columns
    assert "product_name_lenght" in cols and "product_description_lenght" in cols


@pytest.mark.parametrize("contract", OLIST_CONTRACTS, ids=lambda c: c.name)
def test_fixture_headers_match_contract(contract: SourceContract) -> None:
    header, _ = read_header(FIXTURES / contract.file_name)
    validate_header(contract, header)


def test_bom_is_detected_and_stripped_from_header() -> None:
    header, has_bom = read_header(FIXTURES / "product_category_name_translation.csv")
    assert has_bom and header[0] == "product_category_name"


def test_header_mismatch_raises_with_detail() -> None:
    contract = get_contract("olist_sellers")
    with pytest.raises(ContractViolationError, match="missing=\\['seller_state'\\]"):
        validate_header(contract, contract.columns[:-1])
    with pytest.raises(ContractViolationError, match="order differs"):
        validate_header(contract, tuple(reversed(contract.columns)))


def test_missing_and_empty_files(tmp_path: Path) -> None:
    with pytest.raises(SourceFileMissingError):
        describe_file(tmp_path / "nope.csv")
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises(ContractViolationError):
        describe_file(empty)


def test_contract_rejects_bad_natural_key() -> None:
    with pytest.raises(ValueError, match="natural key"):
        SourceContract(name="x", file_name="x.csv", table="x", columns=("a",), natural_key=("b",))


@pytest.mark.parametrize("contract", OLIST_CONTRACTS, ids=lambda c: c.name)
def test_raw_ddl_in_sync_with_contracts(contract: SourceContract) -> None:
    ddl = (ROOT / "database" / "ddl" / "010_raw_olist.sql").read_text(encoding="utf-8")
    block = re.search(rf"create table if not exists raw\.{contract.table} \((.*?)\);", ddl, re.S)
    assert block, contract.table
    cols = [ln.strip().split()[0] for ln in block.group(1).splitlines() if ln.strip()]
    assert tuple(c for c in cols if not c.startswith("_")) == contract.columns
