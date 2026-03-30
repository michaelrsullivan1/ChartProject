from fastapi import APIRouter, Query

from app.services.author_sentiment_view import (
    AuthorSentimentViewRequest,
    build_author_sentiment_view,
)
from app.services.author_vs_btc_view import (
    AuthorTopTweetForWeekRequest,
    AuthorVsBtcViewRequest,
    build_author_top_tweet_for_week,
    build_author_vs_btc_view,
)
from app.services.market_data import fetch_coinbase_spot_price
from app.services.sentiment import DEFAULT_SENTIMENT_MODEL


router = APIRouter(prefix="/views")


def _build_overview_view(
    *,
    username: str,
    view_name: str,
    granularity: str,
    analysis_start: str | None = None,
) -> dict[str, object]:
    return build_author_vs_btc_view(
        AuthorVsBtcViewRequest(
            username=username,
            granularity=granularity,
            view_name=view_name,
            analysis_start=analysis_start,
        )
    )


def _build_overview_top_liked_tweet(
    *,
    username: str,
    view_name: str,
    week_start: str,
) -> dict[str, object]:
    return build_author_top_tweet_for_week(
        AuthorTopTweetForWeekRequest(
            username=username,
            week_start=week_start,
            view_name=view_name,
        )
    )


def _build_overview_sentiment(
    *,
    username: str,
    view_name: str,
    granularity: str,
    model_key: str,
    analysis_start: str | None = None,
) -> dict[str, object]:
    return build_author_sentiment_view(
        AuthorSentimentViewRequest(
            username=username,
            granularity=granularity,
            model_key=model_key,
            view_name=view_name,
            analysis_start=analysis_start,
        )
    )


def _build_btc_spot_price() -> dict[str, object]:
    summary = fetch_coinbase_spot_price(product="BTC-USD")
    return {
        "asset_symbol": summary.asset_symbol,
        "quote_currency": summary.quote_currency,
        "price_usd": summary.price,
        "fetched_at": summary.fetched_at.isoformat().replace("+00:00", "Z"),
        "source_name": summary.source_name,
    }


@router.get("/michael-saylor-overview")
def michael_saylor_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="saylor",
        view_name="michael-saylor-overview",
        granularity=granularity,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/michael-saylor-overview/top-liked-tweet")
def michael_saylor_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="saylor",
        view_name="michael-saylor-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/michael-saylor-overview/sentiment")
def michael_saylor_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="saylor",
        view_name="michael-saylor-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/michael-saylor-overview/btc-spot")
def michael_saylor_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/michael-sullivan-overview")
def michael_sullivan_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="SullyMichaelvan",
        view_name="michael-sullivan-overview",
        granularity=granularity,
    )


@router.get("/michael-sullivan-overview/top-liked-tweet")
def michael_sullivan_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="SullyMichaelvan",
        view_name="michael-sullivan-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/michael-sullivan-overview/sentiment")
def michael_sullivan_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="SullyMichaelvan",
        view_name="michael-sullivan-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
    )


@router.get("/michael-sullivan-overview/btc-spot")
def michael_sullivan_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/micheal-sullivan-overview")
def micheal_sullivan_overview_alias(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return michael_sullivan_overview(granularity=granularity)


@router.get("/micheal-sullivan-overview/top-liked-tweet")
def micheal_sullivan_overview_top_liked_tweet_alias(
    week_start: str = Query(...),
) -> dict[str, object]:
    return michael_sullivan_overview_top_liked_tweet(week_start=week_start)


@router.get("/micheal-sullivan-overview/sentiment")
def micheal_sullivan_overview_sentiment_alias(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return michael_sullivan_overview_sentiment(
        granularity=granularity,
        model_key=model_key,
    )


@router.get("/micheal-sullivan-overview/btc-spot")
def micheal_sullivan_overview_btc_spot_alias() -> dict[str, object]:
    return michael_sullivan_overview_btc_spot()
