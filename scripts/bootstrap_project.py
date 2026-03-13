#!/usr/bin/env python3
from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chartproject.core.config import ensure_directories, load_config
from chartproject.core.logging_config import configure_logging
from chartproject.core.schema_registry import all_schema_statements
from chartproject.core.storage import connect_duckdb, execute_statements

LOGGER = logging.getLogger("bootstrap")
ICONIC_TEMPLATE_HEADERS = [
    "post_id",
    "date",
    "title",
    "summary",
    "importance_score",
    "include_in_animation",
    "notes",
]


def ensure_manual_template(path: Path) -> None:
    if path.exists():
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(ICONIC_TEMPLATE_HEADERS)


if __name__ == "__main__":
    config = load_config()
    configure_logging(config.log_level)

    ensure_directories(config.paths)
    ensure_manual_template(config.paths.manual / "iconic_events.csv")

    connection = connect_duckdb(config.duckdb_path)
    execute_statements(connection, all_schema_statements())
    connection.close()

    LOGGER.info("Bootstrap complete")
    LOGGER.info("Warehouse: %s", config.duckdb_path)
    LOGGER.info("Manual iconic template: %s", config.paths.manual / "iconic_events.csv")
