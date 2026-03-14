from __future__ import annotations

import json
import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from http import HTTPStatus
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from chartproject.domains.social.sources.base import SocialPageResult


@dataclass
class XApiUser:
    user_id: str
    username: str
    display_name: str | None


class XApiV2UserPostsSource:
    """X API v2 source for paginated user tweet/post ingestion."""

    source_name = "x_api_v2"
    api_base = "https://api.x.com/2"

    def __init__(self, bearer_token: str, username: str) -> None:
        if not bearer_token:
            raise ValueError("bearer_token is required for X API source")
        self._bearer_token = bearer_token
        self._username = username
        self._user: XApiUser | None = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._bearer_token}",
            "User-Agent": "chartproject-ingestor/0.1",
        }

    def _http_get(self, path: str, params: dict[str, str]) -> tuple[dict[str, Any], str]:
        query = urlencode(params)
        request_url = f"{self.api_base}{path}?{query}"
        request = Request(url=request_url, headers=self._headers(), method="GET")

        try:
            with urlopen(request, timeout=30) as response:
                payload = response.read().decode("utf-8")
                return json.loads(payload), request_url
        except HTTPError as error:
            if error.code == HTTPStatus.TOO_MANY_REQUESTS:
                reset_seconds = self._rate_limit_reset_seconds(error)
                if reset_seconds is not None and reset_seconds <= 120:
                    time.sleep(reset_seconds)
                    with urlopen(request, timeout=30) as response:
                        payload = response.read().decode("utf-8")
                        return json.loads(payload), request_url
            body = error.read().decode("utf-8", errors="ignore")
            raise RuntimeError(
                f"X API request failed ({error.code}) for {request_url}: {body}"
            ) from error

    def _rate_limit_reset_seconds(self, error: HTTPError) -> int | None:
        reset_header = error.headers.get("x-rate-limit-reset")
        if reset_header and reset_header.isdigit():
            reset_epoch = int(reset_header)
            return max(reset_epoch - int(time.time()) + 1, 1)

        retry_after = error.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return max(int(retry_after), 1)

        http_date = error.headers.get("date")
        if http_date:
            try:
                parsed_date = parsedate_to_datetime(http_date)
                now_epoch = int(parsed_date.timestamp())
                if reset_header and reset_header.isdigit():
                    return max(int(reset_header) - now_epoch + 1, 1)
            except (TypeError, ValueError):
                return None

        return None

    def _get_user(self) -> XApiUser:
        if self._user:
            return self._user

        payload, _ = self._http_get(
            path=f"/users/by/username/{self._username}",
            params={"user.fields": "id,username,name"},
        )
        data = payload.get("data")
        if not data:
            raise RuntimeError(f"No user data returned for username: {self._username}")

        self._user = XApiUser(
            user_id=str(data["id"]),
            username=str(data.get("username", self._username)),
            display_name=data.get("name"),
        )
        return self._user

    def fetch_page(self, cursor: str | None = None, max_results: int = 100) -> SocialPageResult:
        user = self._get_user()
        params = {
            "max_results": str(max(5, min(max_results, 100))),
            "tweet.fields": (
                "id,text,created_at,lang,conversation_id,public_metrics,"
                "referenced_tweets,attachments"
            ),
            "expansions": "attachments.media_keys",
            "media.fields": "media_key,type,url,preview_image_url",
            "exclude": "replies",
        }
        if cursor:
            params["pagination_token"] = cursor

        payload, request_url = self._http_get(path=f"/users/{user.user_id}/tweets", params=params)

        meta = payload.get("meta", {})
        posts = payload.get("data", [])
        includes = payload.get("includes", {})

        return SocialPageResult(
            source_name=self.source_name,
            request_url=request_url,
            raw_payload=json.dumps(payload, ensure_ascii=False),
            raw_extension="json",
            posts=posts,
            includes=includes,
            author_username=user.username,
            author_display_name=user.display_name,
            next_cursor=meta.get("next_token"),
        )
