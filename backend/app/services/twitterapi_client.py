from dataclasses import dataclass

from app.core.config import settings


@dataclass(slots=True)
class TwitterUserFetchRequest:
    user_id: str
    since: str | None = None
    until: str | None = None


class TwitterApiClient:
    """
    Provider boundary for twitterapi.io.

    The project foundation keeps this client isolated so the ingest script,
    parser, and database logic can evolve without coupling everything to one
    request shape.
    """

    def __init__(self) -> None:
        self.base_url = settings.twitterapi_base_url
        self.api_key = settings.twitterapi_api_key

    def fetch_user_tweets(self, request: TwitterUserFetchRequest) -> dict:
        if not self.api_key:
            raise RuntimeError(
                "CHART_TWITTERAPI_API_KEY is not set. Add it in backend/.env before running ingestion."
            )

        raise NotImplementedError(
            "twitterapi.io endpoint wiring is intentionally not implemented in the scaffold yet."
        )
