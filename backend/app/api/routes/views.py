from fastapi import APIRouter, Query

from app.services.author_keyword_heatmap_view import (
    AuthorKeywordHeatmapViewRequest,
    AuthorKeywordTopTweetsRequest,
    AuthorKeywordTrendViewRequest,
    build_author_keyword_heatmap_view,
    build_author_keyword_top_tweets_for_month,
    build_author_keyword_trend_view,
)
from app.services.author_bitcoin_mentions_view import (
    AuthorBitcoinMentionsViewRequest,
    BitcoinMentionsLeaderboardRequest,
    build_author_bitcoin_mentions_view,
    build_bitcoin_mentions_leaderboard,
)
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


def _build_author_keyword_heatmap(
    *,
    username: str,
    view_name: str,
    mode: str,
    word_count: str,
    granularity: str,
    limit: int,
    phrase_query: str | None = None,
    analysis_start: str | None = None,
) -> dict[str, object]:
    return build_author_keyword_heatmap_view(
        AuthorKeywordHeatmapViewRequest(
            username=username,
            mode=mode,
            word_count=word_count,
            granularity=granularity,
            limit=limit,
            phrase_query=phrase_query,
            analysis_start=analysis_start or "2020-08-01T00:00:00Z",
            view_name=view_name,
        )
    )


def _build_author_keyword_trend(
    *,
    username: str,
    view_name: str,
    phrase: str,
    granularity: str,
    analysis_start: str | None = None,
) -> dict[str, object]:
    return build_author_keyword_trend_view(
        AuthorKeywordTrendViewRequest(
            username=username,
            phrase=phrase,
            granularity=granularity,
            analysis_start=analysis_start or "2020-08-01T00:00:00Z",
            view_name=view_name,
        )
    )


def _build_author_keyword_top_tweets(
    *,
    username: str,
    view_name: str,
    phrase: str,
    month_start: str,
    limit: int,
) -> dict[str, object]:
    return build_author_keyword_top_tweets_for_month(
        AuthorKeywordTopTweetsRequest(
            username=username,
            phrase=phrase,
            month_start=month_start,
            limit=limit,
            view_name=view_name,
        )
    )


def _build_author_bitcoin_mentions(
    *,
    username: str,
    phrase: str,
    buy_amount_usd: float,
    view_name: str,
) -> dict[str, object]:
    return build_author_bitcoin_mentions_view(
        AuthorBitcoinMentionsViewRequest(
            username=username,
            phrase=phrase,
            buy_amount_usd=buy_amount_usd,
            view_name=view_name,
        )
    )


def _build_bitcoin_mentions_leaderboard(
    *,
    usernames: list[str] | None,
    phrase: str,
    buy_amount_usd: float,
    view_name: str,
) -> dict[str, object]:
    return build_bitcoin_mentions_leaderboard(
        BitcoinMentionsLeaderboardRequest(
            usernames=usernames,
            phrase=phrase,
            buy_amount_usd=buy_amount_usd,
            view_name=view_name,
        )
    )


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


@router.get("/michael-saylor-heatmap")
def michael_saylor_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="saylor",
        view_name="michael-saylor-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/michael-saylor-heatmap/phrase-trend")
def michael_saylor_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="saylor",
        view_name="michael-saylor-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/michael-saylor-heatmap/top-liked-tweets")
def michael_saylor_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="saylor",
        view_name="michael-saylor-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/michael-sullivan-overview")
def michael_sullivan_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="SullyMichaelvan",
        view_name="michael-sullivan-overview",
        granularity=granularity,
        analysis_start="2024-01-01T00:00:00Z",
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
        analysis_start="2024-01-01T00:00:00Z",
    )


@router.get("/michael-sullivan-overview/btc-spot")
def michael_sullivan_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/michael-sullivan-heatmap")
def michael_sullivan_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="SullyMichaelvan",
        view_name="michael-sullivan-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2024-01-01T00:00:00Z",
    )


@router.get("/michael-sullivan-heatmap/phrase-trend")
def michael_sullivan_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="SullyMichaelvan",
        view_name="michael-sullivan-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2024-01-01T00:00:00Z",
    )


@router.get("/michael-sullivan-heatmap/top-liked-tweets")
def michael_sullivan_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="SullyMichaelvan",
        view_name="michael-sullivan-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/peter-schiff-overview")
def peter_schiff_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="PeterSchiff",
        view_name="peter-schiff-overview",
        granularity=granularity,
        analysis_start="2009-07-14T00:00:00Z",
    )


@router.get("/peter-schiff-overview/top-liked-tweet")
def peter_schiff_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="PeterSchiff",
        view_name="peter-schiff-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/peter-schiff-overview/sentiment")
def peter_schiff_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="PeterSchiff",
        view_name="peter-schiff-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2009-07-14T00:00:00Z",
    )


@router.get("/peter-schiff-overview/btc-spot")
def peter_schiff_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/peter-schiff-heatmap")
def peter_schiff_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="PeterSchiff",
        view_name="peter-schiff-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2009-07-14T00:00:00Z",
    )


@router.get("/peter-schiff-heatmap/phrase-trend")
def peter_schiff_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="PeterSchiff",
        view_name="peter-schiff-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2009-07-14T00:00:00Z",
    )


@router.get("/peter-schiff-heatmap/top-liked-tweets")
def peter_schiff_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="PeterSchiff",
        view_name="peter-schiff-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


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


@router.get("/micheal-sullivan-heatmap")
def micheal_sullivan_heatmap_alias(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return michael_sullivan_heatmap(
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
    )


@router.get("/micheal-sullivan-heatmap/phrase-trend")
def micheal_sullivan_heatmap_phrase_trend_alias(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return michael_sullivan_heatmap_phrase_trend(
        phrase=phrase,
        granularity=granularity,
    )


@router.get("/micheal-sullivan-heatmap/top-liked-tweets")
def micheal_sullivan_heatmap_top_liked_tweets_alias(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return michael_sullivan_heatmap_top_liked_tweets(
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/bitcoin-mentions")
def bitcoin_mentions(
    username: str = Query(...),
    phrase: str = Query(default="bitcoin"),
    buy_amount_usd: float = Query(default=10.0, gt=0),
) -> dict[str, object]:
    return _build_author_bitcoin_mentions(
        username=username,
        phrase=phrase,
        buy_amount_usd=buy_amount_usd,
        view_name="bitcoin-mentions",
    )


@router.get("/bitcoin-mentions/leaderboard")
def bitcoin_mentions_leaderboard(
    username: list[str] | None = Query(default=None),
    phrase: str = Query(default="bitcoin"),
    buy_amount_usd: float = Query(default=10.0, gt=0),
) -> dict[str, object]:
    return _build_bitcoin_mentions_leaderboard(
        usernames=username,
        phrase=phrase,
        buy_amount_usd=buy_amount_usd,
        view_name="bitcoin-mentions-leaderboard",
    )
