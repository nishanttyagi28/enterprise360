"""Unit tests for Data Engineering's ingestion package.
No ingestion/ code existed on 2026-10-30; these skip until it does. Expected API per 05 STTM (ASSUMPTION):
ingestion.loaders / validators exposing row-hash + null normalisation."""
import pytest

pytestmark = pytest.mark.unit
ing = pytest.importorskip("ingestion", reason="ingestion/ package not present yet (Data Engineering)")

def test_null_normalisation():
    v = pytest.importorskip("ingestion.validators")
    fn = getattr(v, "normalise_null", None) or pytest.skip("normalise_null not implemented")
    for x in ["", "NA", "nan", "   "]:
        assert fn(x) is None

def test_row_hash_deterministic():
    l = pytest.importorskip("ingestion.loaders")
    fn = getattr(l, "row_hash", None) or pytest.skip("row_hash not implemented")
    assert fn({"a": "1"}) == fn({"a": "1"}) and len(fn({"a": "1"})) == 64
