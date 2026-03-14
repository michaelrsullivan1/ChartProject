#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

def main() -> None:
    from chartproject.core.schema_registry import all_schema_statements, expected_tables
    from chartproject.core.storage import execute_statements

    connection = duckdb.connect(":memory:")
    execute_statements(connection, all_schema_statements())

    existing_tables = {
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    }
    missing = expected_tables() - existing_tables
    if missing:
        raise SystemExit(f"Missing expected tables: {sorted(missing)}")

    print("Schema validation passed")
    print(f"Created tables: {sorted(existing_tables)}")
    connection.close()


if __name__ == "__main__":
    main()
