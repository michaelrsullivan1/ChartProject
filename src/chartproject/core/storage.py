from __future__ import annotations

from pathlib import Path
from typing import Iterable

import duckdb


def connect_duckdb(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def execute_statements(connection: duckdb.DuckDBPyConnection, statements: Iterable[str]) -> None:
    for statement in statements:
        connection.execute(statement)
