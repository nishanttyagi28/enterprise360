"""File fingerprinting (incremental skip) and row hashing."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from ingestion.extractors import sha256_file
from ingestion.loaders import row_hash
from ingestion.validators import normalise_null

pytestmark = pytest.mark.unit


def test_sha256_file_matches_hashlib_and_is_chunk_independent(tmp_path: Path) -> None:
    f = tmp_path / "a.csv"
    data = b"a,b\n" * 10_000
    f.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert sha256_file(f) == expected
    assert sha256_file(f, chunk_size=7) == expected


def test_sha256_changes_on_any_byte(tmp_path: Path) -> None:
    f = tmp_path / "a.csv"
    f.write_bytes(b"a,b\n1,2\n")
    before = sha256_file(f)
    f.write_bytes(b"a,b\n1,3\n")
    assert sha256_file(f) != before


def test_row_hash_is_order_sensitive_and_separator_safe() -> None:
    assert row_hash({"a": "x,y", "b": "z"}) != row_hash({"a": "x", "b": "y,z"})
    assert row_hash({"a": "1", "b": "2"}, ["a", "b"]) != row_hash({"a": "1", "b": "2"}, ["b", "a"])


def test_row_hash_treats_none_as_empty() -> None:
    assert row_hash({"a": None}) == row_hash({"a": ""})


def test_normalise_null_keeps_real_values() -> None:
    assert normalise_null("  SP ") == "SP"
    assert normalise_null("Nancy") == "Nancy"
    assert normalise_null(None) is None
