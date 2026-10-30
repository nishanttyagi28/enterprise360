"""Schema contracts: the single definition of what a source file must look like."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ReplaceScope(StrEnum):
    """How a reload replaces raw rows.

    TABLE: the file is a full snapshot of the table (Olist: one file per table).
    FILE:  several files feed one table (UCI: one file per period); a reload replaces only the
           rows that came from that file, so files are independently idempotent.
    """

    TABLE = "table"
    FILE = "file"


@dataclass(frozen=True, slots=True)
class SourceContract:
    """Expected shape of one source file and where it lands.

    ``columns`` are the exact source header names, in file order (typos preserved, e.g.
    Olist's ``product_name_lenght``): raw is a verbatim landing zone; renaming happens in dbt.
    ``natural_key`` documents grain and drives the raw index; uniqueness is enforced by dbt
    tests, not by raw constraints, so a bad upstream file still lands and is diagnosable.
    """

    name: str
    file_name: str
    table: str
    columns: tuple[str, ...]
    natural_key: tuple[str, ...]
    schema: str = "raw"
    extra_file_names: tuple[str, ...] = ()
    replace_scope: ReplaceScope = ReplaceScope.TABLE
    # Record the 1-based data-row position as _source_line_no (needed when no natural line key exists)
    track_line_numbers: bool = False

    def __post_init__(self) -> None:
        missing = set(self.natural_key) - set(self.columns)
        if missing:
            raise ValueError(f"{self.name}: natural key columns not in contract: {missing}")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError(f"{self.name}: duplicate columns in contract")
        if self.extra_file_names and self.replace_scope is not ReplaceScope.FILE:
            raise ValueError(f"{self.name}: multiple files require replace_scope=FILE")

    @property
    def file_names(self) -> tuple[str, ...]:
        return (self.file_name, *self.extra_file_names)

    @property
    def qualified_table(self) -> str:
        return f"{self.schema}.{self.table}"
