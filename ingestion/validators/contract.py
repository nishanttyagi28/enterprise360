"""Contract validation. Only structural checks live here; value-level rules belong in dbt tests."""

from __future__ import annotations

from ingestion.exceptions import ContractViolationError
from ingestion.sources.contracts import SourceContract


def validate_header(contract: SourceContract, header: tuple[str, ...]) -> None:
    """Exact, ordered header match. Order matters because COPY maps columns positionally."""
    if header == contract.columns:
        return
    missing = [c for c in contract.columns if c not in header]
    extra = [c for c in header if c not in contract.columns]
    detail = f"missing={missing} unexpected={extra}" if (missing or extra) else "column order differs"
    raise ContractViolationError(f"{contract.file_name}: header does not match contract ({detail})")
