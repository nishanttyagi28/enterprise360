"""Null-token normalisation (STTM §1): '', whitespace, 'NA', 'nan', 'null' -> None.

Raw keeps values verbatim; this function is the Python reference of the rule that dbt
staging applies in SQL (macro ``clean_text``), used for in-Python checks and tests.
"""

from __future__ import annotations

NULL_TOKENS: frozenset[str] = frozenset({"", "na", "nan", "null", "none"})


def normalise_null(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return None if stripped.lower() in NULL_TOKENS else stripped
