from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SocialPageResult:
    source_name: str
    request_url: str
    raw_payload: str
    raw_extension: str
    posts: list[dict]
    includes: dict
    author_username: str
    author_display_name: str | None
    next_cursor: str | None


class SocialDataSource(Protocol):
    source_name: str

    def fetch_page(self, cursor: str | None = None, max_results: int = 100) -> SocialPageResult:
        """Fetch one page of social posts."""
