from fastapi import APIRouter, Query

from app.services.author_vs_btc_view import (
    AuthorTopTweetForWeekRequest,
    AuthorVsBtcViewRequest,
    build_author_top_tweet_for_week,
    build_author_vs_btc_view,
)


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
