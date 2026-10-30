"""File-level extraction helpers: fingerprinting and header reading (no full parse in Python;
the body is streamed to PostgreSQL COPY, which is far faster and quote/newline aware)."""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from ingestion.exceptions import ContractViolationError, SourceFileMissingError

UTF8_BOM = b"\xef\xbb\xbf"


@dataclass(frozen=True, slots=True)
class SourceFile:
    path: Path
    sha256: str
    size_bytes: int
    header: tuple[str, ...]
    has_bom: bool


def sha256_file(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def read_header(path: Path) -> tuple[tuple[str, ...], bool]:
    """Return (header columns, has_bom). Explicit utf-8-sig: Windows tools often add a BOM
    (Olist's translation file ships with one) and the locale default codepage must never apply."""
    with path.open("rb") as raw:
        has_bom = raw.read(3) == UTF8_BOM
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        row = next(csv.reader(fh), None)
    if not row:
        raise ContractViolationError(f"{path.name}: file is empty (no header)")
    return tuple(c.strip() for c in row), has_bom


def describe_file(path: Path) -> SourceFile:
    if not path.is_file():
        raise SourceFileMissingError(f"source file not found: {path}")
    header, has_bom = read_header(path)
    return SourceFile(
        path=path,
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        header=header,
        has_bom=has_bom,
    )
