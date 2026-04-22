from fastapi import APIRouter, Query

from app.services.aggregate_mood_view import (
    AggregateMoodCohortsRequest,
    AggregateMoodMarketSeriesRequest,
    AggregateMoodOverviewRequest,
    AggregateMoodViewRequest,
    build_aggregate_market_series,
    build_cached_aggregate_mood_cohorts,
    build_cached_aggregate_mood_overview,
    build_cached_aggregate_mood_view,
)
from app.services.aggregate_narrative_view import (
    AggregateNarrativeCohortsRequest,
    AggregateNarrativeViewRequest,
    build_cached_aggregate_narrative_cohorts,
    build_cached_aggregate_narrative_view,
)
from app.services.author_bitcoin_mentions_view import (
    AuthorBitcoinMentionsViewRequest,
    BitcoinMentionsLeaderboardRequest,
    build_author_bitcoin_mentions_view,
    build_bitcoin_mentions_leaderboard,
)
from app.services.author_keyword_heatmap_view import (
    AuthorKeywordHeatmapViewRequest,
    AuthorKeywordTopTweetsRequest,
    AuthorKeywordTrendViewRequest,
    build_author_keyword_heatmap_view,
    build_author_keyword_top_tweets_for_month,
    build_author_keyword_trend_view,
)
from app.services.author_mood_view import AuthorMoodViewRequest, build_author_mood_view
from app.services.author_registry import resolve_managed_author_by_slug
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
from app.services.moods import DEFAULT_MOOD_MODEL
from app.services.podcast_person_view import (
    PodcastPersonViewRequest,
    build_podcast_person_view,
)
from app.services.sentiment import DEFAULT_SENTIMENT_MODEL


router = APIRouter(prefix="/views")
AGGREGATE_MOODS_ANALYSIS_START = "2016-01-01T00:00:00Z"


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


def _build_author_moods(
    *,
    username: str,
    view_name: str,
    granularity: str,
    model_key: str,
    analysis_start: str | None = None,
) -> dict[str, object]:
    return build_author_mood_view(
        AuthorMoodViewRequest(
            username=username,
            granularity=granularity,
            model_key=model_key,
            view_name=view_name,
            analysis_start=analysis_start,
        )
    )


def _build_aggregate_moods_overview(
    *,
    view_name: str,
    granularity: str,
    model_key: str,
    analysis_start: str | None = None,
    cohort_tag: str | None = None,
) -> dict[str, object]:
    return build_cached_aggregate_mood_overview(
        AggregateMoodOverviewRequest(
            granularity=granularity,
            model_key=model_key,
            view_name=view_name,
            analysis_start=analysis_start,
            cohort_tag_slug=cohort_tag,
        )
    )


def _build_aggregate_moods(
    *,
    view_name: str,
    granularity: str,
    model_key: str,
    analysis_start: str | None = None,
    cohort_tag: str | None = None,
) -> dict[str, object]:
    return build_cached_aggregate_mood_view(
        AggregateMoodViewRequest(
            granularity=granularity,
            model_key=model_key,
            view_name=view_name,
            analysis_start=analysis_start,
            cohort_tag_slug=cohort_tag,
        )
    )


def _build_aggregate_moods_cohorts(
    *,
    view_name: str,
    model_key: str,
) -> dict[str, object]:
    return build_cached_aggregate_mood_cohorts(
        AggregateMoodCohortsRequest(
            model_key=model_key,
            view_name=view_name,
        )
    )


def _build_aggregate_market_series(
    *,
    view_name: str,
    range_start: str,
    range_end: str,
) -> dict[str, object]:
    return build_aggregate_market_series(
        AggregateMoodMarketSeriesRequest(
            range_start=range_start,
            range_end=range_end,
            view_name=view_name,
        )
    )


def _build_aggregate_narratives(
    *,
    view_name: str,
    granularity: str,
    cohort_tag: str | None = None,
) -> dict[str, object]:
    return build_cached_aggregate_narrative_view(
        AggregateNarrativeViewRequest(
            granularity=granularity,
            cohort_tag_slug=cohort_tag,
            view_name=view_name,
        )
    )


def _build_aggregate_narratives_cohorts(
    *,
    view_name: str,
) -> dict[str, object]:
    return build_cached_aggregate_narrative_cohorts(
        AggregateNarrativeCohortsRequest(
            view_name=view_name,
        )
    )


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


@router.get("/authors/{slug}/overview")
def managed_author_overview(
    slug: str,
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_overview_view(
        username=context.username,
        view_name=f"{context.slug}-overview",
        granularity=granularity,
        analysis_start=context.overview_analysis_start,
    )


@router.get("/authors/{slug}/overview/top-liked-tweet")
def managed_author_overview_top_liked_tweet(
    slug: str,
    week_start: str = Query(...),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_overview_top_liked_tweet(
        username=context.username,
        view_name=f"{context.slug}-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/authors/{slug}/overview/sentiment")
def managed_author_overview_sentiment(
    slug: str,
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_overview_sentiment(
        username=context.username,
        view_name=f"{context.slug}-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start=context.overview_analysis_start,
    )


@router.get("/authors/{slug}/overview/btc-spot")
def managed_author_overview_btc_spot(slug: str) -> dict[str, object]:
    resolve_managed_author_by_slug(slug, require_published=True)
    return _build_btc_spot_price()


@router.get("/authors/{slug}/moods")
def managed_author_moods(
    slug: str,
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_overview_view(
        username=context.username,
        view_name=f"{context.slug}-moods",
        granularity=granularity,
        analysis_start=context.mood_analysis_start,
    )


@router.get("/authors/{slug}/moods/mood-series")
def managed_author_mood_series(
    slug: str,
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_author_moods(
        username=context.username,
        view_name=f"{context.slug}-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start=context.mood_analysis_start,
    )


@router.get("/authors/{slug}/moods/btc-spot")
def managed_author_moods_btc_spot(slug: str) -> dict[str, object]:
    resolve_managed_author_by_slug(slug, require_published=True)
    return _build_btc_spot_price()


@router.get("/authors/{slug}/heatmap")
def managed_author_heatmap(
    slug: str,
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_author_keyword_heatmap(
        username=context.username,
        view_name=f"{context.slug}-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start=context.heatmap_analysis_start,
    )


@router.get("/authors/{slug}/heatmap/phrase-trend")
def managed_author_heatmap_phrase_trend(
    slug: str,
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_author_keyword_trend(
        username=context.username,
        view_name=f"{context.slug}-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start=context.heatmap_analysis_start,
    )


@router.get("/authors/{slug}/heatmap/top-liked-tweets")
def managed_author_heatmap_top_liked_tweets(
    slug: str,
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_author_keyword_top_tweets(
        username=context.username,
        view_name=f"{context.slug}-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/authors/{slug}/bitcoin-mentions")
def managed_author_bitcoin_mentions(
    slug: str,
    phrase: str = Query(default="bitcoin"),
    buy_amount_usd: float = Query(default=10.0, gt=0),
) -> dict[str, object]:
    context = resolve_managed_author_by_slug(slug, require_published=True)
    return _build_author_bitcoin_mentions(
        username=context.username,
        phrase=phrase,
        buy_amount_usd=buy_amount_usd,
        view_name=f"{context.slug}-bitcoin-mentions",
    )


@router.get("/podcasts/persons/{person_slug}")
def podcast_person_view(person_slug: str) -> dict[str, object]:
    return build_podcast_person_view(
        PodcastPersonViewRequest(
            person_slug=person_slug,
            view_name="podcast-person-view",
        )
    )


@router.get("/aggregate-moods")
def aggregate_moods(
    granularity: str = Query(default="week", pattern="^(week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
    cohort_tag: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_aggregate_moods_overview(
        view_name="aggregate-moods",
        granularity=granularity,
        model_key=model_key,
        analysis_start=AGGREGATE_MOODS_ANALYSIS_START,
        cohort_tag=cohort_tag,
    )


@router.get("/aggregate-moods/mood-series")
def aggregate_moods_mood_series(
    granularity: str = Query(default="week", pattern="^(week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
    cohort_tag: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_aggregate_moods(
        view_name="aggregate-moods-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start=AGGREGATE_MOODS_ANALYSIS_START,
        cohort_tag=cohort_tag,
    )


@router.get("/aggregate-moods/btc-spot")
def aggregate_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/aggregate-moods/market-series")
def aggregate_moods_market_series(
    range_start: str = Query(...),
    range_end: str = Query(...),
) -> dict[str, object]:
    return _build_aggregate_market_series(
        view_name="aggregate-moods-market-series",
        range_start=range_start,
        range_end=range_end,
    )


@router.get("/aggregate-moods/cohorts")
def aggregate_moods_cohorts(
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_aggregate_moods_cohorts(
        view_name="aggregate-moods-cohorts",
        model_key=model_key,
    )


@router.get("/aggregate-narratives")
def aggregate_narratives(
    granularity: str = Query(default="week", pattern="^(week)$"),
    cohort_tag: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_aggregate_narratives(
        view_name="aggregate-narratives",
        granularity=granularity,
        cohort_tag=cohort_tag,
    )


@router.get("/aggregate-narratives/cohorts")
def aggregate_narratives_cohorts() -> dict[str, object]:
    return _build_aggregate_narratives_cohorts(
        view_name="aggregate-narratives-cohorts",
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
