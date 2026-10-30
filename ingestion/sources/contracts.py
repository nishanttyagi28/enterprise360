"""Schema contracts: the single definition of what a source file must look like."""

from __future__ import annotations

from dataclasses import dataclass


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

    def __post_init__(self) -> None:
        missing = set(self.natural_key) - set(self.columns)
        if missing:
            raise ValueError(f"{self.name}: natural key columns not in contract: {missing}")
        if len(set(self.columns)) != len(self.columns):
            raise ValueError(f"{self.name}: duplicate columns in contract")

    @property
    def qualified_table(self) -> str:
        return f"{self.schema}.{self.table}"
