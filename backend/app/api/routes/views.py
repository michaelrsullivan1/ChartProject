from fastapi import APIRouter, Query

from app.services.author_vs_btc_view import (
    AuthorTopTweetForWeekRequest,
    AuthorVsBtcViewRequest,
    build_author_top_tweet_for_week,
    build_author_vs_btc_view,
)
from app.services.author_sentiment_view import (
    AuthorSentimentViewRequest,
    build_author_sentiment_view,
)
from app.services.sentiment import DEFAULT_SENTIMENT_MODEL


router = APIRouter(prefix="/views")


@router.get("/michael-saylor-vs-btc")
def michael_saylor_vs_btc_view(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return build_author_vs_btc_view(
        AuthorVsBtcViewRequest(
            username="saylor",
            granularity=granularity,
            view_name="michael-saylor-vs-btc",
        )
    )


@router.get("/michael-saylor-vs-btc/top-liked-tweet")
def michael_saylor_vs_btc_top_liked_tweet_view(
    week_start: str = Query(...),
) -> dict[str, object]:
    return build_author_top_tweet_for_week(
        AuthorTopTweetForWeekRequest(
            username="saylor",
            week_start=week_start,
            view_name="michael-saylor-vs-btc-top-liked-tweet",
        )
    )


@router.get("/michael-saylor-vs-btc/sentiment")
def michael_saylor_vs_btc_sentiment_view(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return build_author_sentiment_view(
        AuthorSentimentViewRequest(
            username="saylor",
            granularity=granularity,
            model_key=model_key,
            view_name="michael-saylor-vs-btc-sentiment",
        )
    )
