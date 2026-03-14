from __future__ import annotations

from pathlib import Path

from chartproject.domains.social.normalization import normalize_social_page
from chartproject.domains.social.sources.base import SocialPageResult


def test_normalize_social_page_maps_fields() -> None:
    page = SocialPageResult(
        source_name="x_api_v2",
        request_url="https://api.x.com/example",
        raw_payload="{}",
        raw_extension="json",
        posts=[
            {
                "id": "123",
                "created_at": "2024-01-15T12:00:00.000Z",
                "text": "Bitcoin is hope",
                "lang": "en",
                "conversation_id": "123",
                "public_metrics": {
                    "like_count": 10,
                    "retweet_count": 2,
                    "reply_count": 1,
                    "quote_count": 0,
                },
                "referenced_tweets": [{"type": "quoted", "id": "55"}],
                "attachments": {"media_keys": ["m1", "m2"]},
            }
        ],
        includes={},
        author_username="saylor",
        author_display_name="Michael Saylor",
        next_cursor="abc",
    )

    frame = normalize_social_page(page, raw_json_path=Path("/tmp/raw_page.json"))

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["post_id"] == "123"
    assert str(row["created_date"]) == "2024-01-15"
    assert row["url"] == "https://x.com/saylor/status/123"
    assert row["like_count"] == 10
    assert row["repost_count"] == 2
    assert bool(row["is_quote"]) is True
    assert bool(row["is_repost"]) is False
    assert bool(row["has_media"]) is True
    assert row["media_count"] == 2
    assert row["source"] == "x_api_v2"
    assert row["raw_json_path"] == "/tmp/raw_page.json"
