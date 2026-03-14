#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

LOGGER = logging.getLogger("check_x_api_setup")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate X API credentials by fetching one page of user posts"
    )
    parser.add_argument("--username", default="saylor", help="X username to test")
    parser.add_argument("--max-results", type=int, default=5, help="Posts to request (5-100)")
    return parser.parse_args()


def main() -> None:
    from chartproject.core.config import load_config
    from chartproject.core.logging_config import configure_logging
    from chartproject.domains.social.sources.x_api import XApiV2UserPostsSource

    args = parse_args()
    config = load_config()
    configure_logging(config.log_level)

    if not config.x_api_bearer_token:
        raise SystemExit(
            "X_API_BEARER_TOKEN is not set. Add it to .env first, then rerun this check."
        )

    source = XApiV2UserPostsSource(
        bearer_token=config.x_api_bearer_token,
        username=args.username,
    )

    try:
        page = source.fetch_page(cursor=None, max_results=args.max_results)
    except RuntimeError as error:
        message = str(error)
        guidance = [
            "Check that the bearer token is from the same App in your X Project.",
            "Confirm your X plan includes API access for this endpoint.",
            "Verify app permissions include read access.",
            "If you just changed app settings, regenerate token and retry.",
        ]
        print(json.dumps({"ok": False, "error": message, "next_steps": guidance}, indent=2))
        raise SystemExit(1) from error

    sample_ids = [post.get("id") for post in page.posts[:3]]
    print(
        json.dumps(
            {
                "ok": True,
                "source": page.source_name,
                "request_url": page.request_url,
                "author_username": page.author_username,
                "fetched_posts": len(page.posts),
                "next_cursor_present": bool(page.next_cursor),
                "sample_post_ids": sample_ids,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
