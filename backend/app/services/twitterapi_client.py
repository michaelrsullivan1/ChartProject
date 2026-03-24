from dataclasses import dataclass
import time
from typing import Any

import httpx
from app.core.config import settings


@dataclass(slots=True)
class TwitterUserInfoRequest:
    username: str


@dataclass(slots=True)
class TwitterUserTimelineRequest:
    user_id: str
    include_replies: bool = True
    include_parent_tweet: bool = False
    cursor: str = ""


class TwitterApiClient:
    """
    Provider boundary for twitterapi.io.

    The project foundation keeps this client isolated so the ingest script,
    parser, and database logic can evolve without coupling everything to one
    request shape.
    """

    def __init__(
        self,
        *,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self.base_url = settings.twitterapi_base_url.rstrip("/")
        self.api_key = settings.twitterapi_api_key
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._client = httpx.Client(timeout=timeout_seconds)

    def __enter__(self) -> "TwitterApiClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def get_user_info(self, request: TwitterUserInfoRequest) -> dict[str, Any]:
        return self._get_json(
            "/twitter/user/info",
            params={"userName": request.username},
        )

    def get_user_timeline_page(
        self,
        request: TwitterUserTimelineRequest,
    ) -> dict[str, Any]:
        return self._get_json(
            "/twitter/user/tweet_timeline",
            params={
                "userId": request.user_id,
                "includeReplies": str(request.include_replies).lower(),
                "includeParentTweet": str(request.include_parent_tweet).lower(),
                "cursor": request.cursor,
            },
        )

    def _get_json(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key:
            raise RuntimeError(
                "CHART_TWITTERAPI_API_KEY is not set. Add it in backend/.env before running ingestion."
            )
        last_error: Exception | None = None
        attempts = max(1, self.max_retries)

        for attempt in range(1, attempts + 1):
            try:
                response = self._client.get(
                    f"{self.base_url}{path}",
                    params=params,
                    headers={"X-API-Key": self.api_key},
                )
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, dict):
                    raise RuntimeError(
                        f"twitterapi.io returned a non-object payload for {path}."
                    )

                payload_status = payload.get("status")
                if payload_status == "error":
                    message = payload.get("message") or payload.get("msg") or "Unknown API error"
                    raise RuntimeError(f"twitterapi.io returned an error for {path}: {message}")

                return payload
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code < 500 and status_code != 429:
                    body = exc.response.text[:500]
                    raise RuntimeError(
                        f"twitterapi.io request failed for {path} with status "
                        f"{status_code}: {body}"
                    ) from exc
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
            except RuntimeError as exc:
                last_error = exc
                raise

            if attempt < attempts:
                time.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))

        if isinstance(last_error, httpx.HTTPStatusError):
            body = last_error.response.text[:500]
            raise RuntimeError(
                f"twitterapi.io request failed for {path} with status "
                f"{last_error.response.status_code}: {body}"
            ) from last_error

        if last_error is not None:
            raise RuntimeError(f"twitterapi.io request failed for {path}: {last_error}") from last_error

        raise RuntimeError(f"twitterapi.io request failed for {path} for an unknown reason.")
