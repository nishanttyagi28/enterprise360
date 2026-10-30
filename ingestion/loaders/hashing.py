"""Row hashing. ``_row_hash`` is computed inside PostgreSQL during the load (no Python round
trip per row); :func:`row_hash` is the byte-identical Python reference used by tests and tools.

Definition: sha256_hex( utf8( join(U+001F, [value or '' for each source column in file order]) ) )
U+001F (unit separator) cannot occur in Olist text, so ('a,b','c') and ('a','b,c') differ.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from psycopg import sql

ROW_HASH_SEPARATOR = "\x1f"


def row_hash(row: Mapping[str, str | None], columns: Sequence[str] | None = None) -> str:
    cols = list(columns) if columns is not None else list(row.keys())
    payload = ROW_HASH_SEPARATOR.join(row.get(c) or "" for c in cols)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def row_hash_sql(columns: Sequence[str]) -> sql.Composed:
    parts = sql.SQL(", ").join(sql.SQL("coalesce({}, '')").format(sql.Identifier(c)) for c in columns)
    return sql.SQL("encode(sha256(convert_to(concat_ws(chr(31), {}), 'UTF8')), 'hex')").format(parts)
