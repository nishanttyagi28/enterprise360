"""Run dbt with the repo .env loaded and the in-repo profile, from any CWD / OS.

Usage: ``python -m orchestration.dbt_runner build`` (any dbt args are passed through).
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from orchestration.env import DBT_PROJECT_DIR, load_env


class DbtCommandError(RuntimeError):
    """dbt finished with failures (model errors or failing error-severity tests)."""


def run_dbt(args: Sequence[str]) -> None:
    load_env()
    from dbt.cli.main import dbtRunner  # imported late: env must be loaded first

    full_args = [
        *args,
        "--project-dir",
        str(DBT_PROJECT_DIR),
        "--profiles-dir",
        str(DBT_PROJECT_DIR),
    ]
    result = dbtRunner().invoke(full_args)
    if result.exception is not None:
        raise DbtCommandError(f"dbt {' '.join(args)} crashed: {result.exception}") from result.exception
    if not result.success:
        raise DbtCommandError(f"dbt {' '.join(args)} reported failures")


def main(argv: Sequence[str] | None = None) -> int:
    try:
        run_dbt(list(sys.argv[1:] if argv is None else argv))
    except DbtCommandError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
