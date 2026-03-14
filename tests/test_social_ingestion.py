from __future__ import annotations

from pathlib import Path

from chartproject.core.schema_registry import all_schema_statements
from chartproject.core.storage import connect_duckdb, execute_statements
from chartproject.domains.social.ingestion import ingest_social_posts, load_checkpoint
from chartproject.domains.social.sources.base import SocialPageResult


class FakeSocialSource:
    source_name = "fake_social"

    def __init__(self, pages: list[SocialPageResult]) -> None:
        self.pages = pages
        self.calls = 0

    def fetch_page(self, cursor: str | None = None, max_results: int = 100) -> SocialPageResult:
        page = self.pages[self.calls]
        self.calls += 1
        return page


def _make_page(post_id: str, next_cursor: str | None) -> SocialPageResult:
    return SocialPageResult(
        source_name="fake_social",
        request_url="https://example.test",
        raw_payload="{}",
        raw_extension="json",
        posts=[
            {
                "id": post_id,
                "created_at": "2024-01-01T00:00:00.000Z",
                "text": f"post {post_id}",
                "lang": "en",
                "conversation_id": post_id,
                "public_metrics": {},
            }
        ],
        includes={},
        author_username="saylor",
        author_display_name="Michael Saylor",
        next_cursor=next_cursor,
    )


def test_ingest_social_posts_resumes_from_checkpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "analytics.duckdb"
    checkpoint = tmp_path / "checkpoint.json"
    raw_dir = tmp_path / "raw"

    connection = connect_duckdb(db_path)
    execute_statements(connection, all_schema_statements())
    connection.close()

    source = FakeSocialSource(
        pages=[
            _make_page("1", next_cursor="token-2"),
            _make_page("2", next_cursor=None),
        ]
    )

    first_run = ingest_social_posts(
        source=source,
        username="saylor",
        raw_social_dir=raw_dir,
        warehouse_path=db_path,
        checkpoint_path=checkpoint,
        max_pages=1,
        resume=True,
    )
    assert first_run["completed"] is False
    assert first_run["pages_fetched"] == 1

    second_run = ingest_social_posts(
        source=source,
        username="saylor",
        raw_social_dir=raw_dir,
        warehouse_path=db_path,
        checkpoint_path=checkpoint,
        resume=True,
    )
    assert second_run["completed"] is True
    assert second_run["pages_fetched"] == 2

    connection = connect_duckdb(db_path)
    row_count = connection.execute("SELECT COUNT(*) FROM raw_social_posts").fetchone()[0]
    connection.close()
    assert row_count == 2

    final_checkpoint = load_checkpoint(checkpoint)
    assert final_checkpoint is not None
    assert final_checkpoint.completed is True
