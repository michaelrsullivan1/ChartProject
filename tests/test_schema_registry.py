import duckdb

from chartproject.core.schema_registry import all_schema_statements, expected_tables
from chartproject.core.storage import execute_statements


def test_expected_tables_can_be_created() -> None:
    connection = duckdb.connect(":memory:")
    execute_statements(connection, all_schema_statements())

    created_tables = {
        row[0]
        for row in connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    }
    assert expected_tables().issubset(created_tables)
    connection.close()
