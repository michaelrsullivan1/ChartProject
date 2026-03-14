from __future__ import annotations

from pathlib import Path

import pandas as pd

from chartproject.domains.social.sources.base import SocialPageResult


def normalize_social_page(page: SocialPageResult, raw_json_path: Path) -> pd.DataFrame:
    records: list[dict] = []
    for post in page.posts:
        post_id = str(post.get("id", "")).strip()
        if not post_id:
            continue

        created_ts = pd.to_datetime(post.get("created_at"), utc=True, errors="coerce")
        public_metrics = post.get("public_metrics") or {}
        referenced = post.get("referenced_tweets") or []
        referenced_types = {item.get("type") for item in referenced if isinstance(item, dict)}

        media_keys = (post.get("attachments") or {}).get("media_keys") or []
        media_count = len(media_keys)

        records.append(
            {
                "post_id": post_id,
                "created_at": created_ts,
                "created_date": created_ts.date() if pd.notna(created_ts) else None,
                "text": post.get("text") or "",
                "url": f"https://x.com/{page.author_username}/status/{post_id}",
                "author_username": page.author_username,
                "author_display_name": page.author_display_name,
                "like_count": int(public_metrics.get("like_count", 0) or 0),
                "repost_count": int(public_metrics.get("retweet_count", 0) or 0),
                "reply_count": int(public_metrics.get("reply_count", 0) or 0),
                "quote_count": int(public_metrics.get("quote_count", 0) or 0),
                "view_count": None,
                "is_repost": "retweeted" in referenced_types,
                "is_quote": "quoted" in referenced_types,
                "has_media": media_count > 0,
                "media_count": media_count,
                "language": post.get("lang"),
                "source": page.source_name,
                "conversation_id": str(post.get("conversation_id") or "") or None,
                "raw_json_path": str(raw_json_path),
            }
        )

    frame = pd.DataFrame(records)
    if frame.empty:
        return frame

    frame = frame.drop_duplicates(subset=["post_id"], keep="last")
    frame = frame.sort_values("created_at")
    return frame.reset_index(drop=True)
