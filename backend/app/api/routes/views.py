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
from app.services.author_registry import resolve_managed_author_by_slug
from app.services.author_sentiment_view import (
    AuthorSentimentViewRequest,
    build_author_sentiment_view,
)
from app.services.author_mood_view import AuthorMoodViewRequest, build_author_mood_view
from app.services.author_vs_btc_view import (
    AuthorTopTweetForWeekRequest,
    AuthorVsBtcViewRequest,
    build_author_top_tweet_for_week,
    build_author_vs_btc_view,
)
from app.services.market_data import fetch_coinbase_spot_price
from app.services.moods import DEFAULT_MOOD_MODEL
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


@router.get("/michael-saylor-moods")
def michael_saylor_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="saylor",
        view_name="michael-saylor-moods",
        granularity=granularity,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/michael-saylor-moods/mood-series")
def michael_saylor_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="saylor",
        view_name="michael-saylor-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/michael-saylor-moods/btc-spot")
def michael_saylor_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/peter-schiff-moods")
def peter_schiff_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="PeterSchiff",
        view_name="peter-schiff-moods",
        granularity=granularity,
        analysis_start="2009-07-14T00:00:00Z",
    )


@router.get("/peter-schiff-moods/mood-series")
def peter_schiff_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="PeterSchiff",
        view_name="peter-schiff-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2009-07-14T00:00:00Z",
    )


@router.get("/peter-schiff-moods/btc-spot")
def peter_schiff_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/aggregate-moods")
def aggregate_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
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
def aggregate_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
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
def aggregate_mood_cohorts(
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_aggregate_moods_cohorts(
        view_name="aggregate-moods-cohorts",
        model_key=model_key,
    )


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


@router.get("/walker-america-overview")
def walker_america_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="WalkerAmerica",
        view_name="walker-america-overview",
        granularity=granularity,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/chris-millas-overview")
def chris_millas_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ChrisMMillas",
        view_name="chris-millas-overview",
        granularity=granularity,
        analysis_start="2024-09-09T00:00:00Z",
    )


@router.get("/richard-byworth-overview")
def richard_byworth_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="RichardByworth",
        view_name="richard-byworth-overview",
        granularity=granularity,
        analysis_start="2019-03-01T00:00:00Z",
    )


@router.get("/andrew-webley-overview")
def andrew_webley_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="asjwebley",
        view_name="andrew-webley-overview",
        granularity=granularity,
        analysis_start="2018-04-17T00:00:00Z",
    )


@router.get("/ray-overview")
def ray_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="artificialsub",
        view_name="ray-overview",
        granularity=granularity,
        analysis_start="2023-03-18T00:00:00Z",
    )


@router.get("/stack-hodler-overview")
def stack_hodler_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="stackhodler",
        view_name="stack-hodler-overview",
        granularity=granularity,
        analysis_start="2020-05-05T00:00:00Z",
    )


@router.get("/isabella-overview")
def isabella_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="isabellasg3",
        view_name="isabella-overview",
        granularity=granularity,
        analysis_start="2021-06-10T00:00:00Z",
    )


@router.get("/oliver-velez-overview")
def oliver_velez_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="olvelez007",
        view_name="oliver-velez-overview",
        granularity=granularity,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/ben-werkman-overview")
def ben_werkman_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Werkman",
        view_name="ben-werkman-overview",
        granularity=granularity,
        analysis_start="2021-01-24T00:00:00Z",
    )


@router.get("/brian-brookshire-overview")
def brian_brookshire_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="btc_overflow",
        view_name="brian-brookshire-overview",
        granularity=granularity,
        analysis_start="2023-03-25T00:00:00Z",
    )


@router.get("/brian-armstrong-overview")
def brian_armstrong_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="brian_armstrong",
        view_name="brian-armstrong-overview",
        granularity=granularity,
        analysis_start="2021-04-07T00:00:00Z",
    )


@router.get("/cz-bnb-overview")
def cz_bnb_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="cz_binance",
        view_name="cz-bnb-overview",
        granularity=granularity,
        analysis_start="2018-01-15T00:00:00Z",
    )


@router.get("/arthur-hayes-overview")
def arthur_hayes_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="CryptoHayes",
        view_name="arthur-hayes-overview",
        granularity=granularity,
        analysis_start="2018-04-11T00:00:00Z",
    )


@router.get("/jesse-powell-overview")
def jesse_powell_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="jespow",
        view_name="jesse-powell-overview",
        granularity=granularity,
        analysis_start="2015-03-05T00:00:00Z",
    )


@router.get("/jack-mallers-overview")
def jack_mallers_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="jackmallers",
        view_name="jack-mallers-overview",
        granularity=granularity,
        analysis_start="2015-04-07T00:00:00Z",
    )


@router.get("/zynx-overview")
def zynx_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ZynxBTC",
        view_name="zynx-overview",
        granularity=granularity,
        analysis_start="2022-02-18T00:00:00Z",
    )


@router.get("/jesse-myers-overview")
def jesse_myers_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Croesus_BTC",
        view_name="jesse-myers-overview",
        granularity=granularity,
        analysis_start="2018-06-06T00:00:00Z",
    )


@router.get("/willy-woo-overview")
def willy_woo_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="willywoo",
        view_name="willy-woo-overview",
        granularity=granularity,
        analysis_start="2015-03-12T00:00:00Z",
    )


@router.get("/andy-edstrom-overview")
def andy_edstrom_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="edstromandrew",
        view_name="andy-edstrom-overview",
        granularity=granularity,
        analysis_start="2017-12-29T00:00:00Z",
    )


@router.get("/dan-hillery-overview")
def dan_hillery_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="hillery_dan",
        view_name="dan-hillery-overview",
        granularity=granularity,
        analysis_start="2022-12-29T00:00:00Z",
    )


@router.get("/adrian-morris-overview")
def adrian_morris_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="_Adrian",
        view_name="adrian-morris-overview",
        granularity=granularity,
        analysis_start="2015-11-12T00:00:00Z",
    )


@router.get("/jeff-walton-overview")
def jeff_walton_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="PunterJeff",
        view_name="jeff-walton-overview",
        granularity=granularity,
        analysis_start="2015-11-09T00:00:00Z",
    )


@router.get("/nithu-sezni-overview")
def nithu_sezni_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="nithusezni",
        view_name="nithu-sezni-overview",
        granularity=granularity,
        analysis_start="2022-10-31T00:00:00Z",
    )


@router.get("/mason-overview")
def mason_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="MasonFoard",
        view_name="mason-overview",
        granularity=granularity,
        analysis_start="2021-03-14T00:00:00Z",
    )


@router.get("/british-hodl-overview")
def british_hodl_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BritishHodl",
        view_name="british-hodl-overview",
        granularity=granularity,
        analysis_start="2021-08-27T00:00:00Z",
    )


@router.get("/lyn-alden-overview")
def lyn_alden_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="LynAldenContact",
        view_name="lyn-alden-overview",
        granularity=granularity,
        analysis_start="2017-01-25T00:00:00Z",
    )


@router.get("/professor-b21-overview")
def professor_b21_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ProfessorB21",
        view_name="professor-b21-overview",
        granularity=granularity,
        analysis_start="2024-09-04T00:00:00Z",
    )


@router.get("/btc-gus-overview")
def btc_gus_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Scavacini777",
        view_name="btc-gus-overview",
        granularity=granularity,
        analysis_start="2022-05-03T00:00:00Z",
    )


@router.get("/bit-paine-overview")
def bit_paine_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BitPaine",
        view_name="bit-paine-overview",
        granularity=granularity,
        analysis_start="2021-11-28T00:00:00Z",
    )


@router.get("/matt-cole-overview")
def matt_cole_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ColeMacro",
        view_name="matt-cole-overview",
        granularity=granularity,
        analysis_start="2021-12-02T00:00:00Z",
    )


@router.get("/parker-lewis-overview")
def parker_lewis_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="parkeralewis",
        view_name="parker-lewis-overview",
        granularity=granularity,
        analysis_start="2017-12-30T00:00:00Z",
    )


@router.get("/kristen-overview")
def kristen_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="2dogs1chic",
        view_name="kristen-overview",
        granularity=granularity,
        analysis_start="2024-04-30T00:00:00Z",
    )


@router.get("/dana-in-hawaii-overview")
def dana_in_hawaii_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Danainhawaii",
        view_name="dana-in-hawaii-overview",
        granularity=granularity,
        analysis_start="2022-09-23T00:00:00Z",
    )


@router.get("/parabolic-code-overview")
def parabolic_code_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ParabolicCode",
        view_name="parabolic-code-overview",
        granularity=granularity,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/bitquant-overview")
def bitquant_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BitQua",
        view_name="bitquant-overview",
        granularity=granularity,
        analysis_start="2021-09-16T00:00:00Z",
    )


@router.get("/ed-juline-overview")
def ed_juline_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ejuline",
        view_name="ed-juline-overview",
        granularity=granularity,
        analysis_start="2020-01-12T00:00:00Z",
    )


@router.get("/alex-thorn-overview")
def alex_thorn_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="intangiblecoins",
        view_name="alex-thorn-overview",
        granularity=granularity,
        analysis_start="2017-08-25T00:00:00Z",
    )


@router.get("/btc-teacher-overview")
def btc_teacher_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BitcoinTeacher_",
        view_name="btc-teacher-overview",
        granularity=granularity,
        analysis_start="2025-11-12T00:00:00Z",
    )


@router.get("/roaring-ragnar-overview")
def roaring_ragnar_overview(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="RoaringRagnar",
        view_name="roaring-ragnar-overview",
        granularity=granularity,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/walker-america-overview/top-liked-tweet")
def walker_america_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="WalkerAmerica",
        view_name="walker-america-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/chris-millas-overview/top-liked-tweet")
def chris_millas_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="ChrisMMillas",
        view_name="chris-millas-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/richard-byworth-overview/top-liked-tweet")
def richard_byworth_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="RichardByworth",
        view_name="richard-byworth-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/andrew-webley-overview/top-liked-tweet")
def andrew_webley_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="asjwebley",
        view_name="andrew-webley-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/ray-overview/top-liked-tweet")
def ray_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="artificialsub",
        view_name="ray-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/stack-hodler-overview/top-liked-tweet")
def stack_hodler_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="stackhodler",
        view_name="stack-hodler-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/isabella-overview/top-liked-tweet")
def isabella_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="isabellasg3",
        view_name="isabella-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/oliver-velez-overview/top-liked-tweet")
def oliver_velez_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="olvelez007",
        view_name="oliver-velez-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/ben-werkman-overview/top-liked-tweet")
def ben_werkman_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="Werkman",
        view_name="ben-werkman-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/brian-brookshire-overview/top-liked-tweet")
def brian_brookshire_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="btc_overflow",
        view_name="brian-brookshire-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/brian-armstrong-overview/top-liked-tweet")
def brian_armstrong_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="brian_armstrong",
        view_name="brian-armstrong-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/cz-bnb-overview/top-liked-tweet")
def cz_bnb_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="cz_binance",
        view_name="cz-bnb-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/arthur-hayes-overview/top-liked-tweet")
def arthur_hayes_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="CryptoHayes",
        view_name="arthur-hayes-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/jesse-powell-overview/top-liked-tweet")
def jesse_powell_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="jespow",
        view_name="jesse-powell-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/jack-mallers-overview/top-liked-tweet")
def jack_mallers_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="jackmallers",
        view_name="jack-mallers-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/zynx-overview/top-liked-tweet")
def zynx_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="ZynxBTC",
        view_name="zynx-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/jesse-myers-overview/top-liked-tweet")
def jesse_myers_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="Croesus_BTC",
        view_name="jesse-myers-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/willy-woo-overview/top-liked-tweet")
def willy_woo_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="willywoo",
        view_name="willy-woo-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/andy-edstrom-overview/top-liked-tweet")
def andy_edstrom_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="edstromandrew",
        view_name="andy-edstrom-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/dan-hillery-overview/top-liked-tweet")
def dan_hillery_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="hillery_dan",
        view_name="dan-hillery-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/adrian-morris-overview/top-liked-tweet")
def adrian_morris_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="_Adrian",
        view_name="adrian-morris-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/jeff-walton-overview/top-liked-tweet")
def jeff_walton_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="PunterJeff",
        view_name="jeff-walton-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/nithu-sezni-overview/top-liked-tweet")
def nithu_sezni_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="nithusezni",
        view_name="nithu-sezni-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/mason-overview/top-liked-tweet")
def mason_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="MasonFoard",
        view_name="mason-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/british-hodl-overview/top-liked-tweet")
def british_hodl_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="BritishHodl",
        view_name="british-hodl-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/lyn-alden-overview/top-liked-tweet")
def lyn_alden_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="LynAldenContact",
        view_name="lyn-alden-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/professor-b21-overview/top-liked-tweet")
def professor_b21_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="ProfessorB21",
        view_name="professor-b21-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/btc-gus-overview/top-liked-tweet")
def btc_gus_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="Scavacini777",
        view_name="btc-gus-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/bit-paine-overview/top-liked-tweet")
def bit_paine_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="BitPaine",
        view_name="bit-paine-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/matt-cole-overview/top-liked-tweet")
def matt_cole_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="ColeMacro",
        view_name="matt-cole-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/parker-lewis-overview/top-liked-tweet")
def parker_lewis_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="parkeralewis",
        view_name="parker-lewis-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/kristen-overview/top-liked-tweet")
def kristen_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="2dogs1chic",
        view_name="kristen-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/dana-in-hawaii-overview/top-liked-tweet")
def dana_in_hawaii_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="Danainhawaii",
        view_name="dana-in-hawaii-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/parabolic-code-overview/top-liked-tweet")
def parabolic_code_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="ParabolicCode",
        view_name="parabolic-code-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/bitquant-overview/top-liked-tweet")
def bitquant_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="BitQua",
        view_name="bitquant-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/ed-juline-overview/top-liked-tweet")
def ed_juline_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="ejuline",
        view_name="ed-juline-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/alex-thorn-overview/top-liked-tweet")
def alex_thorn_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="intangiblecoins",
        view_name="alex-thorn-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/btc-teacher-overview/top-liked-tweet")
def btc_teacher_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="BitcoinTeacher_",
        view_name="btc-teacher-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/roaring-ragnar-overview/top-liked-tweet")
def roaring_ragnar_overview_top_liked_tweet(
    week_start: str = Query(...),
) -> dict[str, object]:
    return _build_overview_top_liked_tweet(
        username="RoaringRagnar",
        view_name="roaring-ragnar-overview-top-liked-tweet",
        week_start=week_start,
    )


@router.get("/walker-america-overview/sentiment")
def walker_america_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="WalkerAmerica",
        view_name="walker-america-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/chris-millas-overview/sentiment")
def chris_millas_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="ChrisMMillas",
        view_name="chris-millas-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-09-09T00:00:00Z",
    )


@router.get("/richard-byworth-overview/sentiment")
def richard_byworth_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="RichardByworth",
        view_name="richard-byworth-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2019-03-01T00:00:00Z",
    )


@router.get("/andrew-webley-overview/sentiment")
def andrew_webley_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="asjwebley",
        view_name="andrew-webley-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-04-17T00:00:00Z",
    )


@router.get("/ray-overview/sentiment")
def ray_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="artificialsub",
        view_name="ray-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2023-03-18T00:00:00Z",
    )


@router.get("/stack-hodler-overview/sentiment")
def stack_hodler_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="stackhodler",
        view_name="stack-hodler-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-05-05T00:00:00Z",
    )


@router.get("/isabella-overview/sentiment")
def isabella_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="isabellasg3",
        view_name="isabella-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-06-10T00:00:00Z",
    )


@router.get("/oliver-velez-overview/sentiment")
def oliver_velez_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="olvelez007",
        view_name="oliver-velez-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/ben-werkman-overview/sentiment")
def ben_werkman_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="Werkman",
        view_name="ben-werkman-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-01-24T00:00:00Z",
    )


@router.get("/brian-brookshire-overview/sentiment")
def brian_brookshire_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="btc_overflow",
        view_name="brian-brookshire-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2023-03-25T00:00:00Z",
    )


@router.get("/brian-armstrong-overview/sentiment")
def brian_armstrong_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="brian_armstrong",
        view_name="brian-armstrong-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-04-07T00:00:00Z",
    )


@router.get("/cz-bnb-overview/sentiment")
def cz_bnb_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="cz_binance",
        view_name="cz-bnb-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-01-15T00:00:00Z",
    )


@router.get("/arthur-hayes-overview/sentiment")
def arthur_hayes_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="CryptoHayes",
        view_name="arthur-hayes-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-04-11T00:00:00Z",
    )


@router.get("/jesse-powell-overview/sentiment")
def jesse_powell_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="jespow",
        view_name="jesse-powell-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-03-05T00:00:00Z",
    )


@router.get("/jack-mallers-overview/sentiment")
def jack_mallers_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="jackmallers",
        view_name="jack-mallers-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-04-07T00:00:00Z",
    )


@router.get("/zynx-overview/sentiment")
def zynx_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="ZynxBTC",
        view_name="zynx-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-02-18T00:00:00Z",
    )


@router.get("/jesse-myers-overview/sentiment")
def jesse_myers_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="Croesus_BTC",
        view_name="jesse-myers-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-06-06T00:00:00Z",
    )


@router.get("/willy-woo-overview/sentiment")
def willy_woo_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="willywoo",
        view_name="willy-woo-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-03-12T00:00:00Z",
    )


@router.get("/andy-edstrom-overview/sentiment")
def andy_edstrom_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="edstromandrew",
        view_name="andy-edstrom-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-12-29T00:00:00Z",
    )


@router.get("/dan-hillery-overview/sentiment")
def dan_hillery_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="hillery_dan",
        view_name="dan-hillery-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-12-29T00:00:00Z",
    )


@router.get("/adrian-morris-overview/sentiment")
def adrian_morris_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="_Adrian",
        view_name="adrian-morris-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-11-12T00:00:00Z",
    )


@router.get("/jeff-walton-overview/sentiment")
def jeff_walton_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="PunterJeff",
        view_name="jeff-walton-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-11-09T00:00:00Z",
    )


@router.get("/nithu-sezni-overview/sentiment")
def nithu_sezni_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="nithusezni",
        view_name="nithu-sezni-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-10-31T00:00:00Z",
    )


@router.get("/mason-overview/sentiment")
def mason_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="MasonFoard",
        view_name="mason-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-03-14T00:00:00Z",
    )


@router.get("/british-hodl-overview/sentiment")
def british_hodl_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="BritishHodl",
        view_name="british-hodl-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-08-27T00:00:00Z",
    )


@router.get("/lyn-alden-overview/sentiment")
def lyn_alden_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="LynAldenContact",
        view_name="lyn-alden-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-01-25T00:00:00Z",
    )


@router.get("/professor-b21-overview/sentiment")
def professor_b21_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="ProfessorB21",
        view_name="professor-b21-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-09-04T00:00:00Z",
    )


@router.get("/btc-gus-overview/sentiment")
def btc_gus_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="Scavacini777",
        view_name="btc-gus-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-05-03T00:00:00Z",
    )


@router.get("/bit-paine-overview/sentiment")
def bit_paine_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="BitPaine",
        view_name="bit-paine-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-11-28T00:00:00Z",
    )


@router.get("/matt-cole-overview/sentiment")
def matt_cole_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="ColeMacro",
        view_name="matt-cole-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-12-02T00:00:00Z",
    )


@router.get("/parker-lewis-overview/sentiment")
def parker_lewis_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="parkeralewis",
        view_name="parker-lewis-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-12-30T00:00:00Z",
    )


@router.get("/kristen-overview/sentiment")
def kristen_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="2dogs1chic",
        view_name="kristen-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-04-30T00:00:00Z",
    )


@router.get("/dana-in-hawaii-overview/sentiment")
def dana_in_hawaii_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="Danainhawaii",
        view_name="dana-in-hawaii-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-09-23T00:00:00Z",
    )


@router.get("/parabolic-code-overview/sentiment")
def parabolic_code_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="ParabolicCode",
        view_name="parabolic-code-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/bitquant-overview/sentiment")
def bitquant_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="BitQua",
        view_name="bitquant-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-09-16T00:00:00Z",
    )


@router.get("/ed-juline-overview/sentiment")
def ed_juline_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="ejuline",
        view_name="ed-juline-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-01-12T00:00:00Z",
    )


@router.get("/alex-thorn-overview/sentiment")
def alex_thorn_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="intangiblecoins",
        view_name="alex-thorn-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-08-25T00:00:00Z",
    )


@router.get("/btc-teacher-overview/sentiment")
def btc_teacher_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="BitcoinTeacher_",
        view_name="btc-teacher-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2025-11-12T00:00:00Z",
    )


@router.get("/roaring-ragnar-overview/sentiment")
def roaring_ragnar_overview_sentiment(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_SENTIMENT_MODEL),
) -> dict[str, object]:
    return _build_overview_sentiment(
        username="RoaringRagnar",
        view_name="roaring-ragnar-overview-sentiment",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/walker-america-overview/btc-spot")
def walker_america_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/chris-millas-overview/btc-spot")
def chris_millas_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/richard-byworth-overview/btc-spot")
def richard_byworth_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/andrew-webley-overview/btc-spot")
def andrew_webley_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/ray-overview/btc-spot")
def ray_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/stack-hodler-overview/btc-spot")
def stack_hodler_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/isabella-overview/btc-spot")
def isabella_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/oliver-velez-overview/btc-spot")
def oliver_velez_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/ben-werkman-overview/btc-spot")
def ben_werkman_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/brian-brookshire-overview/btc-spot")
def brian_brookshire_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/brian-armstrong-overview/btc-spot")
def brian_armstrong_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/cz-bnb-overview/btc-spot")
def cz_bnb_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/arthur-hayes-overview/btc-spot")
def arthur_hayes_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jesse-powell-overview/btc-spot")
def jesse_powell_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jack-mallers-overview/btc-spot")
def jack_mallers_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/zynx-overview/btc-spot")
def zynx_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jesse-myers-overview/btc-spot")
def jesse_myers_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/willy-woo-overview/btc-spot")
def willy_woo_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/andy-edstrom-overview/btc-spot")
def andy_edstrom_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/dan-hillery-overview/btc-spot")
def dan_hillery_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/adrian-morris-overview/btc-spot")
def adrian_morris_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jeff-walton-overview/btc-spot")
def jeff_walton_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/nithu-sezni-overview/btc-spot")
def nithu_sezni_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/mason-overview/btc-spot")
def mason_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/british-hodl-overview/btc-spot")
def british_hodl_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/lyn-alden-overview/btc-spot")
def lyn_alden_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/professor-b21-overview/btc-spot")
def professor_b21_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/btc-gus-overview/btc-spot")
def btc_gus_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/bit-paine-overview/btc-spot")
def bit_paine_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/matt-cole-overview/btc-spot")
def matt_cole_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/parker-lewis-overview/btc-spot")
def parker_lewis_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/kristen-overview/btc-spot")
def kristen_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/dana-in-hawaii-overview/btc-spot")
def dana_in_hawaii_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/parabolic-code-overview/btc-spot")
def parabolic_code_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/bitquant-overview/btc-spot")
def bitquant_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/ed-juline-overview/btc-spot")
def ed_juline_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/alex-thorn-overview/btc-spot")
def alex_thorn_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/btc-teacher-overview/btc-spot")
def btc_teacher_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/roaring-ragnar-overview/btc-spot")
def roaring_ragnar_overview_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/walker-america-moods")
def walker_america_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="WalkerAmerica",
        view_name="walker-america-moods",
        granularity=granularity,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/chris-millas-moods")
def chris_millas_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ChrisMMillas",
        view_name="chris-millas-moods",
        granularity=granularity,
        analysis_start="2024-09-09T00:00:00Z",
    )


@router.get("/richard-byworth-moods")
def richard_byworth_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="RichardByworth",
        view_name="richard-byworth-moods",
        granularity=granularity,
        analysis_start="2019-03-01T00:00:00Z",
    )


@router.get("/andrew-webley-moods")
def andrew_webley_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="asjwebley",
        view_name="andrew-webley-moods",
        granularity=granularity,
        analysis_start="2018-04-17T00:00:00Z",
    )


@router.get("/ray-moods")
def ray_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="artificialsub",
        view_name="ray-moods",
        granularity=granularity,
        analysis_start="2023-03-18T00:00:00Z",
    )


@router.get("/stack-hodler-moods")
def stack_hodler_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="stackhodler",
        view_name="stack-hodler-moods",
        granularity=granularity,
        analysis_start="2020-05-05T00:00:00Z",
    )


@router.get("/isabella-moods")
def isabella_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="isabellasg3",
        view_name="isabella-moods",
        granularity=granularity,
        analysis_start="2021-06-10T00:00:00Z",
    )


@router.get("/oliver-velez-moods")
def oliver_velez_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="olvelez007",
        view_name="oliver-velez-moods",
        granularity=granularity,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/ben-werkman-moods")
def ben_werkman_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Werkman",
        view_name="ben-werkman-moods",
        granularity=granularity,
        analysis_start="2021-01-24T00:00:00Z",
    )


@router.get("/brian-brookshire-moods")
def brian_brookshire_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="btc_overflow",
        view_name="brian-brookshire-moods",
        granularity=granularity,
        analysis_start="2023-03-25T00:00:00Z",
    )


@router.get("/brian-armstrong-moods")
def brian_armstrong_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="brian_armstrong",
        view_name="brian-armstrong-moods",
        granularity=granularity,
        analysis_start="2021-04-07T00:00:00Z",
    )


@router.get("/cz-bnb-moods")
def cz_bnb_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="cz_binance",
        view_name="cz-bnb-moods",
        granularity=granularity,
        analysis_start="2018-01-15T00:00:00Z",
    )


@router.get("/arthur-hayes-moods")
def arthur_hayes_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="CryptoHayes",
        view_name="arthur-hayes-moods",
        granularity=granularity,
        analysis_start="2018-04-11T00:00:00Z",
    )


@router.get("/jesse-powell-moods")
def jesse_powell_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="jespow",
        view_name="jesse-powell-moods",
        granularity=granularity,
        analysis_start="2015-03-05T00:00:00Z",
    )


@router.get("/jack-mallers-moods")
def jack_mallers_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="jackmallers",
        view_name="jack-mallers-moods",
        granularity=granularity,
        analysis_start="2015-04-07T00:00:00Z",
    )


@router.get("/zynx-moods")
def zynx_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ZynxBTC",
        view_name="zynx-moods",
        granularity=granularity,
        analysis_start="2022-02-18T00:00:00Z",
    )


@router.get("/jesse-myers-moods")
def jesse_myers_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Croesus_BTC",
        view_name="jesse-myers-moods",
        granularity=granularity,
        analysis_start="2018-06-06T00:00:00Z",
    )


@router.get("/willy-woo-moods")
def willy_woo_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="willywoo",
        view_name="willy-woo-moods",
        granularity=granularity,
        analysis_start="2015-03-12T00:00:00Z",
    )


@router.get("/andy-edstrom-moods")
def andy_edstrom_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="edstromandrew",
        view_name="andy-edstrom-moods",
        granularity=granularity,
        analysis_start="2017-12-29T00:00:00Z",
    )


@router.get("/dan-hillery-moods")
def dan_hillery_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="hillery_dan",
        view_name="dan-hillery-moods",
        granularity=granularity,
        analysis_start="2022-12-29T00:00:00Z",
    )


@router.get("/adrian-morris-moods")
def adrian_morris_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="_Adrian",
        view_name="adrian-morris-moods",
        granularity=granularity,
        analysis_start="2015-11-12T00:00:00Z",
    )


@router.get("/jeff-walton-moods")
def jeff_walton_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="PunterJeff",
        view_name="jeff-walton-moods",
        granularity=granularity,
        analysis_start="2015-11-09T00:00:00Z",
    )


@router.get("/nithu-sezni-moods")
def nithu_sezni_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="nithusezni",
        view_name="nithu-sezni-moods",
        granularity=granularity,
        analysis_start="2022-10-31T00:00:00Z",
    )


@router.get("/mason-moods")
def mason_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="MasonFoard",
        view_name="mason-moods",
        granularity=granularity,
        analysis_start="2021-03-14T00:00:00Z",
    )


@router.get("/british-hodl-moods")
def british_hodl_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BritishHodl",
        view_name="british-hodl-moods",
        granularity=granularity,
        analysis_start="2021-08-27T00:00:00Z",
    )


@router.get("/lyn-alden-moods")
def lyn_alden_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="LynAldenContact",
        view_name="lyn-alden-moods",
        granularity=granularity,
        analysis_start="2017-01-25T00:00:00Z",
    )


@router.get("/professor-b21-moods")
def professor_b21_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ProfessorB21",
        view_name="professor-b21-moods",
        granularity=granularity,
        analysis_start="2024-09-04T00:00:00Z",
    )


@router.get("/btc-gus-moods")
def btc_gus_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Scavacini777",
        view_name="btc-gus-moods",
        granularity=granularity,
        analysis_start="2022-05-03T00:00:00Z",
    )


@router.get("/bit-paine-moods")
def bit_paine_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BitPaine",
        view_name="bit-paine-moods",
        granularity=granularity,
        analysis_start="2021-11-28T00:00:00Z",
    )


@router.get("/matt-cole-moods")
def matt_cole_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ColeMacro",
        view_name="matt-cole-moods",
        granularity=granularity,
        analysis_start="2021-12-02T00:00:00Z",
    )


@router.get("/parker-lewis-moods")
def parker_lewis_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="parkeralewis",
        view_name="parker-lewis-moods",
        granularity=granularity,
        analysis_start="2017-12-30T00:00:00Z",
    )


@router.get("/kristen-moods")
def kristen_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="2dogs1chic",
        view_name="kristen-moods",
        granularity=granularity,
        analysis_start="2024-04-30T00:00:00Z",
    )


@router.get("/dana-in-hawaii-moods")
def dana_in_hawaii_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="Danainhawaii",
        view_name="dana-in-hawaii-moods",
        granularity=granularity,
        analysis_start="2022-09-23T00:00:00Z",
    )


@router.get("/parabolic-code-moods")
def parabolic_code_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ParabolicCode",
        view_name="parabolic-code-moods",
        granularity=granularity,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/bitquant-moods")
def bitquant_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BitQua",
        view_name="bitquant-moods",
        granularity=granularity,
        analysis_start="2021-09-16T00:00:00Z",
    )


@router.get("/ed-juline-moods")
def ed_juline_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="ejuline",
        view_name="ed-juline-moods",
        granularity=granularity,
        analysis_start="2020-01-12T00:00:00Z",
    )


@router.get("/alex-thorn-moods")
def alex_thorn_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="intangiblecoins",
        view_name="alex-thorn-moods",
        granularity=granularity,
        analysis_start="2017-08-25T00:00:00Z",
    )


@router.get("/btc-teacher-moods")
def btc_teacher_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="BitcoinTeacher_",
        view_name="btc-teacher-moods",
        granularity=granularity,
        analysis_start="2025-11-12T00:00:00Z",
    )


@router.get("/roaring-ragnar-moods")
def roaring_ragnar_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="RoaringRagnar",
        view_name="roaring-ragnar-moods",
        granularity=granularity,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/walker-america-moods/mood-series")
def walker_america_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="WalkerAmerica",
        view_name="walker-america-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/chris-millas-moods/mood-series")
def chris_millas_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="ChrisMMillas",
        view_name="chris-millas-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-09-09T00:00:00Z",
    )


@router.get("/richard-byworth-moods/mood-series")
def richard_byworth_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="RichardByworth",
        view_name="richard-byworth-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2019-03-01T00:00:00Z",
    )


@router.get("/andrew-webley-moods/mood-series")
def andrew_webley_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="asjwebley",
        view_name="andrew-webley-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-04-17T00:00:00Z",
    )


@router.get("/ray-moods/mood-series")
def ray_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="artificialsub",
        view_name="ray-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2023-03-18T00:00:00Z",
    )


@router.get("/stack-hodler-moods/mood-series")
def stack_hodler_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="stackhodler",
        view_name="stack-hodler-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-05-05T00:00:00Z",
    )


@router.get("/isabella-moods/mood-series")
def isabella_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="isabellasg3",
        view_name="isabella-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-06-10T00:00:00Z",
    )


@router.get("/oliver-velez-moods/mood-series")
def oliver_velez_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="olvelez007",
        view_name="oliver-velez-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/ben-werkman-moods/mood-series")
def ben_werkman_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="Werkman",
        view_name="ben-werkman-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-01-24T00:00:00Z",
    )


@router.get("/brian-brookshire-moods/mood-series")
def brian_brookshire_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="btc_overflow",
        view_name="brian-brookshire-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2023-03-25T00:00:00Z",
    )


@router.get("/brian-armstrong-moods/mood-series")
def brian_armstrong_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="brian_armstrong",
        view_name="brian-armstrong-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-04-07T00:00:00Z",
    )


@router.get("/cz-bnb-moods/mood-series")
def cz_bnb_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="cz_binance",
        view_name="cz-bnb-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-01-15T00:00:00Z",
    )


@router.get("/arthur-hayes-moods/mood-series")
def arthur_hayes_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="CryptoHayes",
        view_name="arthur-hayes-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-04-11T00:00:00Z",
    )


@router.get("/jesse-powell-moods/mood-series")
def jesse_powell_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="jespow",
        view_name="jesse-powell-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-03-05T00:00:00Z",
    )


@router.get("/jack-mallers-moods/mood-series")
def jack_mallers_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="jackmallers",
        view_name="jack-mallers-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-04-07T00:00:00Z",
    )


@router.get("/zynx-moods/mood-series")
def zynx_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="ZynxBTC",
        view_name="zynx-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-02-18T00:00:00Z",
    )


@router.get("/jesse-myers-moods/mood-series")
def jesse_myers_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="Croesus_BTC",
        view_name="jesse-myers-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2018-06-06T00:00:00Z",
    )


@router.get("/willy-woo-moods/mood-series")
def willy_woo_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="willywoo",
        view_name="willy-woo-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-03-12T00:00:00Z",
    )


@router.get("/andy-edstrom-moods/mood-series")
def andy_edstrom_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="edstromandrew",
        view_name="andy-edstrom-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-12-29T00:00:00Z",
    )


@router.get("/dan-hillery-moods/mood-series")
def dan_hillery_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="hillery_dan",
        view_name="dan-hillery-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-12-29T00:00:00Z",
    )


@router.get("/adrian-morris-moods/mood-series")
def adrian_morris_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="_Adrian",
        view_name="adrian-morris-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-11-12T00:00:00Z",
    )


@router.get("/jeff-walton-moods/mood-series")
def jeff_walton_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="PunterJeff",
        view_name="jeff-walton-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2015-11-09T00:00:00Z",
    )


@router.get("/nithu-sezni-moods/mood-series")
def nithu_sezni_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="nithusezni",
        view_name="nithu-sezni-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-10-31T00:00:00Z",
    )


@router.get("/mason-moods/mood-series")
def mason_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="MasonFoard",
        view_name="mason-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-03-14T00:00:00Z",
    )


@router.get("/british-hodl-moods/mood-series")
def british_hodl_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="BritishHodl",
        view_name="british-hodl-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-08-27T00:00:00Z",
    )


@router.get("/lyn-alden-moods/mood-series")
def lyn_alden_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="LynAldenContact",
        view_name="lyn-alden-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-01-25T00:00:00Z",
    )


@router.get("/professor-b21-moods/mood-series")
def professor_b21_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="ProfessorB21",
        view_name="professor-b21-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-09-04T00:00:00Z",
    )


@router.get("/btc-gus-moods/mood-series")
def btc_gus_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="Scavacini777",
        view_name="btc-gus-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-05-03T00:00:00Z",
    )


@router.get("/bit-paine-moods/mood-series")
def bit_paine_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="BitPaine",
        view_name="bit-paine-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-11-28T00:00:00Z",
    )


@router.get("/matt-cole-moods/mood-series")
def matt_cole_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="ColeMacro",
        view_name="matt-cole-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-12-02T00:00:00Z",
    )


@router.get("/parker-lewis-moods/mood-series")
def parker_lewis_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="parkeralewis",
        view_name="parker-lewis-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-12-30T00:00:00Z",
    )


@router.get("/kristen-moods/mood-series")
def kristen_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="2dogs1chic",
        view_name="kristen-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-04-30T00:00:00Z",
    )


@router.get("/dana-in-hawaii-moods/mood-series")
def dana_in_hawaii_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="Danainhawaii",
        view_name="dana-in-hawaii-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2022-09-23T00:00:00Z",
    )


@router.get("/parabolic-code-moods/mood-series")
def parabolic_code_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="ParabolicCode",
        view_name="parabolic-code-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/bitquant-moods/mood-series")
def bitquant_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="BitQua",
        view_name="bitquant-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2021-09-16T00:00:00Z",
    )


@router.get("/ed-juline-moods/mood-series")
def ed_juline_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="ejuline",
        view_name="ed-juline-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2020-01-12T00:00:00Z",
    )


@router.get("/alex-thorn-moods/mood-series")
def alex_thorn_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="intangiblecoins",
        view_name="alex-thorn-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2017-08-25T00:00:00Z",
    )


@router.get("/btc-teacher-moods/mood-series")
def btc_teacher_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="BitcoinTeacher_",
        view_name="btc-teacher-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2025-11-12T00:00:00Z",
    )


@router.get("/roaring-ragnar-moods/mood-series")
def roaring_ragnar_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="RoaringRagnar",
        view_name="roaring-ragnar-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/walker-america-moods/btc-spot")
def walker_america_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/chris-millas-moods/btc-spot")
def chris_millas_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/richard-byworth-moods/btc-spot")
def richard_byworth_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/andrew-webley-moods/btc-spot")
def andrew_webley_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/ray-moods/btc-spot")
def ray_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/stack-hodler-moods/btc-spot")
def stack_hodler_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/isabella-moods/btc-spot")
def isabella_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/oliver-velez-moods/btc-spot")
def oliver_velez_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/ben-werkman-moods/btc-spot")
def ben_werkman_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/brian-brookshire-moods/btc-spot")
def brian_brookshire_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/brian-armstrong-moods/btc-spot")
def brian_armstrong_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/cz-bnb-moods/btc-spot")
def cz_bnb_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/arthur-hayes-moods/btc-spot")
def arthur_hayes_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jesse-powell-moods/btc-spot")
def jesse_powell_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jack-mallers-moods/btc-spot")
def jack_mallers_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/zynx-moods/btc-spot")
def zynx_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jesse-myers-moods/btc-spot")
def jesse_myers_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/willy-woo-moods/btc-spot")
def willy_woo_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/andy-edstrom-moods/btc-spot")
def andy_edstrom_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/dan-hillery-moods/btc-spot")
def dan_hillery_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/adrian-morris-moods/btc-spot")
def adrian_morris_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/jeff-walton-moods/btc-spot")
def jeff_walton_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/nithu-sezni-moods/btc-spot")
def nithu_sezni_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/mason-moods/btc-spot")
def mason_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/british-hodl-moods/btc-spot")
def british_hodl_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/lyn-alden-moods/btc-spot")
def lyn_alden_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/professor-b21-moods/btc-spot")
def professor_b21_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/btc-gus-moods/btc-spot")
def btc_gus_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/bit-paine-moods/btc-spot")
def bit_paine_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/matt-cole-moods/btc-spot")
def matt_cole_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/parker-lewis-moods/btc-spot")
def parker_lewis_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/kristen-moods/btc-spot")
def kristen_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/dana-in-hawaii-moods/btc-spot")
def dana_in_hawaii_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/parabolic-code-moods/btc-spot")
def parabolic_code_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/bitquant-moods/btc-spot")
def bitquant_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/ed-juline-moods/btc-spot")
def ed_juline_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/alex-thorn-moods/btc-spot")
def alex_thorn_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/btc-teacher-moods/btc-spot")
def btc_teacher_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/roaring-ragnar-moods/btc-spot")
def roaring_ragnar_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


@router.get("/walker-america-heatmap")
def walker_america_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="WalkerAmerica",
        view_name="walker-america-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/chris-millas-heatmap")
def chris_millas_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="ChrisMMillas",
        view_name="chris-millas-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2024-09-09T00:00:00Z",
    )


@router.get("/richard-byworth-heatmap")
def richard_byworth_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="RichardByworth",
        view_name="richard-byworth-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2019-03-01T00:00:00Z",
    )


@router.get("/andrew-webley-heatmap")
def andrew_webley_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="asjwebley",
        view_name="andrew-webley-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2018-04-17T00:00:00Z",
    )


@router.get("/ray-heatmap")
def ray_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="artificialsub",
        view_name="ray-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2023-03-18T00:00:00Z",
    )


@router.get("/stack-hodler-heatmap")
def stack_hodler_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="stackhodler",
        view_name="stack-hodler-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2020-05-05T00:00:00Z",
    )


@router.get("/isabella-heatmap")
def isabella_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="isabellasg3",
        view_name="isabella-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-06-10T00:00:00Z",
    )


@router.get("/oliver-velez-heatmap")
def oliver_velez_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="olvelez007",
        view_name="oliver-velez-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/ben-werkman-heatmap")
def ben_werkman_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="Werkman",
        view_name="ben-werkman-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-01-24T00:00:00Z",
    )


@router.get("/brian-brookshire-heatmap")
def brian_brookshire_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="btc_overflow",
        view_name="brian-brookshire-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2023-03-25T00:00:00Z",
    )


@router.get("/brian-armstrong-heatmap")
def brian_armstrong_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="brian_armstrong",
        view_name="brian-armstrong-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-04-07T00:00:00Z",
    )


@router.get("/cz-bnb-heatmap")
def cz_bnb_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="cz_binance",
        view_name="cz-bnb-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2018-01-15T00:00:00Z",
    )


@router.get("/arthur-hayes-heatmap")
def arthur_hayes_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="CryptoHayes",
        view_name="arthur-hayes-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2018-04-11T00:00:00Z",
    )


@router.get("/jesse-powell-heatmap")
def jesse_powell_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="jespow",
        view_name="jesse-powell-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2015-03-05T00:00:00Z",
    )


@router.get("/jack-mallers-heatmap")
def jack_mallers_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="jackmallers",
        view_name="jack-mallers-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2015-04-07T00:00:00Z",
    )


@router.get("/zynx-heatmap")
def zynx_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="ZynxBTC",
        view_name="zynx-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2022-02-18T00:00:00Z",
    )


@router.get("/jesse-myers-heatmap")
def jesse_myers_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="Croesus_BTC",
        view_name="jesse-myers-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2018-06-06T00:00:00Z",
    )


@router.get("/willy-woo-heatmap")
def willy_woo_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="willywoo",
        view_name="willy-woo-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2015-03-12T00:00:00Z",
    )


@router.get("/andy-edstrom-heatmap")
def andy_edstrom_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="edstromandrew",
        view_name="andy-edstrom-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2017-12-29T00:00:00Z",
    )


@router.get("/dan-hillery-heatmap")
def dan_hillery_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="hillery_dan",
        view_name="dan-hillery-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2022-12-29T00:00:00Z",
    )


@router.get("/adrian-morris-heatmap")
def adrian_morris_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="_Adrian",
        view_name="adrian-morris-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2015-11-12T00:00:00Z",
    )


@router.get("/jeff-walton-heatmap")
def jeff_walton_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="PunterJeff",
        view_name="jeff-walton-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2015-11-09T00:00:00Z",
    )


@router.get("/nithu-sezni-heatmap")
def nithu_sezni_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="nithusezni",
        view_name="nithu-sezni-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2022-10-31T00:00:00Z",
    )


@router.get("/mason-heatmap")
def mason_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="MasonFoard",
        view_name="mason-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-03-14T00:00:00Z",
    )


@router.get("/british-hodl-heatmap")
def british_hodl_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="BritishHodl",
        view_name="british-hodl-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-08-27T00:00:00Z",
    )


@router.get("/lyn-alden-heatmap")
def lyn_alden_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="LynAldenContact",
        view_name="lyn-alden-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2017-01-25T00:00:00Z",
    )


@router.get("/professor-b21-heatmap")
def professor_b21_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="ProfessorB21",
        view_name="professor-b21-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2024-09-04T00:00:00Z",
    )


@router.get("/btc-gus-heatmap")
def btc_gus_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="Scavacini777",
        view_name="btc-gus-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2022-05-03T00:00:00Z",
    )


@router.get("/bit-paine-heatmap")
def bit_paine_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="BitPaine",
        view_name="bit-paine-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-11-28T00:00:00Z",
    )


@router.get("/matt-cole-heatmap")
def matt_cole_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="ColeMacro",
        view_name="matt-cole-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-12-02T00:00:00Z",
    )


@router.get("/parker-lewis-heatmap")
def parker_lewis_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="parkeralewis",
        view_name="parker-lewis-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2017-12-30T00:00:00Z",
    )


@router.get("/kristen-heatmap")
def kristen_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="2dogs1chic",
        view_name="kristen-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2024-04-30T00:00:00Z",
    )


@router.get("/dana-in-hawaii-heatmap")
def dana_in_hawaii_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="Danainhawaii",
        view_name="dana-in-hawaii-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2022-09-23T00:00:00Z",
    )


@router.get("/parabolic-code-heatmap")
def parabolic_code_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="ParabolicCode",
        view_name="parabolic-code-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/bitquant-heatmap")
def bitquant_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="BitQua",
        view_name="bitquant-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2021-09-16T00:00:00Z",
    )


@router.get("/ed-juline-heatmap")
def ed_juline_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="ejuline",
        view_name="ed-juline-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2020-01-12T00:00:00Z",
    )


@router.get("/alex-thorn-heatmap")
def alex_thorn_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="intangiblecoins",
        view_name="alex-thorn-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2017-08-25T00:00:00Z",
    )


@router.get("/btc-teacher-heatmap")
def btc_teacher_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="BitcoinTeacher_",
        view_name="btc-teacher-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2025-11-12T00:00:00Z",
    )


@router.get("/roaring-ragnar-heatmap")
def roaring_ragnar_heatmap(
    mode: str = Query(default="common", pattern="^(all|common|rising)$"),
    word_count: str = Query(default="all", pattern="^(all|1|2|3)$"),
    granularity: str = Query(default="month", pattern="^(month)$"),
    limit: int = Query(default=48, ge=1, le=120),
    phrase_query: str | None = Query(default=None),
) -> dict[str, object]:
    return _build_author_keyword_heatmap(
        username="RoaringRagnar",
        view_name="roaring-ragnar-heatmap",
        mode=mode,
        word_count=word_count,
        granularity=granularity,
        limit=limit,
        phrase_query=phrase_query,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/walker-america-heatmap/phrase-trend")
def walker_america_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="WalkerAmerica",
        view_name="walker-america-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2020-08-01T00:00:00Z",
    )


@router.get("/chris-millas-heatmap/phrase-trend")
def chris_millas_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="ChrisMMillas",
        view_name="chris-millas-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2024-09-09T00:00:00Z",
    )


@router.get("/richard-byworth-heatmap/phrase-trend")
def richard_byworth_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="RichardByworth",
        view_name="richard-byworth-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2019-03-01T00:00:00Z",
    )


@router.get("/andrew-webley-heatmap/phrase-trend")
def andrew_webley_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="asjwebley",
        view_name="andrew-webley-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2018-04-17T00:00:00Z",
    )


@router.get("/ray-heatmap/phrase-trend")
def ray_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="artificialsub",
        view_name="ray-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2023-03-18T00:00:00Z",
    )


@router.get("/stack-hodler-heatmap/phrase-trend")
def stack_hodler_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="stackhodler",
        view_name="stack-hodler-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2020-05-05T00:00:00Z",
    )


@router.get("/isabella-heatmap/phrase-trend")
def isabella_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="isabellasg3",
        view_name="isabella-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-06-10T00:00:00Z",
    )


@router.get("/oliver-velez-heatmap/phrase-trend")
def oliver_velez_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="olvelez007",
        view_name="oliver-velez-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2020-01-01T00:00:00Z",
    )


@router.get("/ben-werkman-heatmap/phrase-trend")
def ben_werkman_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="Werkman",
        view_name="ben-werkman-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-01-24T00:00:00Z",
    )


@router.get("/brian-brookshire-heatmap/phrase-trend")
def brian_brookshire_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="btc_overflow",
        view_name="brian-brookshire-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2023-03-25T00:00:00Z",
    )


@router.get("/brian-armstrong-heatmap/phrase-trend")
def brian_armstrong_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="brian_armstrong",
        view_name="brian-armstrong-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-04-07T00:00:00Z",
    )


@router.get("/cz-bnb-heatmap/phrase-trend")
def cz_bnb_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="cz_binance",
        view_name="cz-bnb-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2018-01-15T00:00:00Z",
    )


@router.get("/arthur-hayes-heatmap/phrase-trend")
def arthur_hayes_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="CryptoHayes",
        view_name="arthur-hayes-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2018-04-11T00:00:00Z",
    )


@router.get("/jesse-powell-heatmap/phrase-trend")
def jesse_powell_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="jespow",
        view_name="jesse-powell-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2015-03-05T00:00:00Z",
    )


@router.get("/jack-mallers-heatmap/phrase-trend")
def jack_mallers_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="jackmallers",
        view_name="jack-mallers-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2015-04-07T00:00:00Z",
    )


@router.get("/zynx-heatmap/phrase-trend")
def zynx_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="ZynxBTC",
        view_name="zynx-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2022-02-18T00:00:00Z",
    )


@router.get("/jesse-myers-heatmap/phrase-trend")
def jesse_myers_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="Croesus_BTC",
        view_name="jesse-myers-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2018-06-06T00:00:00Z",
    )


@router.get("/willy-woo-heatmap/phrase-trend")
def willy_woo_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="willywoo",
        view_name="willy-woo-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2015-03-12T00:00:00Z",
    )


@router.get("/andy-edstrom-heatmap/phrase-trend")
def andy_edstrom_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="edstromandrew",
        view_name="andy-edstrom-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2017-12-29T00:00:00Z",
    )


@router.get("/dan-hillery-heatmap/phrase-trend")
def dan_hillery_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="hillery_dan",
        view_name="dan-hillery-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2022-12-29T00:00:00Z",
    )


@router.get("/adrian-morris-heatmap/phrase-trend")
def adrian_morris_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="_Adrian",
        view_name="adrian-morris-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2015-11-12T00:00:00Z",
    )


@router.get("/jeff-walton-heatmap/phrase-trend")
def jeff_walton_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="PunterJeff",
        view_name="jeff-walton-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2015-11-09T00:00:00Z",
    )


@router.get("/nithu-sezni-heatmap/phrase-trend")
def nithu_sezni_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="nithusezni",
        view_name="nithu-sezni-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2022-10-31T00:00:00Z",
    )


@router.get("/mason-heatmap/phrase-trend")
def mason_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="MasonFoard",
        view_name="mason-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-03-14T00:00:00Z",
    )


@router.get("/british-hodl-heatmap/phrase-trend")
def british_hodl_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="BritishHodl",
        view_name="british-hodl-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-08-27T00:00:00Z",
    )


@router.get("/lyn-alden-heatmap/phrase-trend")
def lyn_alden_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="LynAldenContact",
        view_name="lyn-alden-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2017-01-25T00:00:00Z",
    )


@router.get("/professor-b21-heatmap/phrase-trend")
def professor_b21_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="ProfessorB21",
        view_name="professor-b21-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2024-09-04T00:00:00Z",
    )


@router.get("/btc-gus-heatmap/phrase-trend")
def btc_gus_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="Scavacini777",
        view_name="btc-gus-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2022-05-03T00:00:00Z",
    )


@router.get("/bit-paine-heatmap/phrase-trend")
def bit_paine_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="BitPaine",
        view_name="bit-paine-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-11-28T00:00:00Z",
    )


@router.get("/matt-cole-heatmap/phrase-trend")
def matt_cole_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="ColeMacro",
        view_name="matt-cole-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-12-02T00:00:00Z",
    )


@router.get("/parker-lewis-heatmap/phrase-trend")
def parker_lewis_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="parkeralewis",
        view_name="parker-lewis-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2017-12-30T00:00:00Z",
    )


@router.get("/kristen-heatmap/phrase-trend")
def kristen_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="2dogs1chic",
        view_name="kristen-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2024-04-30T00:00:00Z",
    )


@router.get("/dana-in-hawaii-heatmap/phrase-trend")
def dana_in_hawaii_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="Danainhawaii",
        view_name="dana-in-hawaii-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2022-09-23T00:00:00Z",
    )


@router.get("/parabolic-code-heatmap/phrase-trend")
def parabolic_code_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="ParabolicCode",
        view_name="parabolic-code-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/bitquant-heatmap/phrase-trend")
def bitquant_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="BitQua",
        view_name="bitquant-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2021-09-16T00:00:00Z",
    )


@router.get("/ed-juline-heatmap/phrase-trend")
def ed_juline_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="ejuline",
        view_name="ed-juline-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2020-01-12T00:00:00Z",
    )


@router.get("/alex-thorn-heatmap/phrase-trend")
def alex_thorn_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="intangiblecoins",
        view_name="alex-thorn-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2017-08-25T00:00:00Z",
    )


@router.get("/btc-teacher-heatmap/phrase-trend")
def btc_teacher_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="BitcoinTeacher_",
        view_name="btc-teacher-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2025-11-12T00:00:00Z",
    )


@router.get("/roaring-ragnar-heatmap/phrase-trend")
def roaring_ragnar_heatmap_phrase_trend(
    phrase: str = Query(...),
    granularity: str = Query(default="month", pattern="^(month)$"),
) -> dict[str, object]:
    return _build_author_keyword_trend(
        username="RoaringRagnar",
        view_name="roaring-ragnar-heatmap-phrase-trend",
        phrase=phrase,
        granularity=granularity,
        analysis_start="2025-01-10T00:00:00Z",
    )


@router.get("/walker-america-heatmap/top-liked-tweets")
def walker_america_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="WalkerAmerica",
        view_name="walker-america-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/chris-millas-heatmap/top-liked-tweets")
def chris_millas_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="ChrisMMillas",
        view_name="chris-millas-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/richard-byworth-heatmap/top-liked-tweets")
def richard_byworth_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="RichardByworth",
        view_name="richard-byworth-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/andrew-webley-heatmap/top-liked-tweets")
def andrew_webley_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="asjwebley",
        view_name="andrew-webley-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/ray-heatmap/top-liked-tweets")
def ray_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="artificialsub",
        view_name="ray-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/stack-hodler-heatmap/top-liked-tweets")
def stack_hodler_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="stackhodler",
        view_name="stack-hodler-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/isabella-heatmap/top-liked-tweets")
def isabella_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="isabellasg3",
        view_name="isabella-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/oliver-velez-heatmap/top-liked-tweets")
def oliver_velez_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="olvelez007",
        view_name="oliver-velez-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/ben-werkman-heatmap/top-liked-tweets")
def ben_werkman_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="Werkman",
        view_name="ben-werkman-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/brian-brookshire-heatmap/top-liked-tweets")
def brian_brookshire_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="btc_overflow",
        view_name="brian-brookshire-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/brian-armstrong-heatmap/top-liked-tweets")
def brian_armstrong_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="brian_armstrong",
        view_name="brian-armstrong-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/cz-bnb-heatmap/top-liked-tweets")
def cz_bnb_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="cz_binance",
        view_name="cz-bnb-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/arthur-hayes-heatmap/top-liked-tweets")
def arthur_hayes_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="CryptoHayes",
        view_name="arthur-hayes-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/jesse-powell-heatmap/top-liked-tweets")
def jesse_powell_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="jespow",
        view_name="jesse-powell-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/jack-mallers-heatmap/top-liked-tweets")
def jack_mallers_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="jackmallers",
        view_name="jack-mallers-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/zynx-heatmap/top-liked-tweets")
def zynx_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="ZynxBTC",
        view_name="zynx-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/jesse-myers-heatmap/top-liked-tweets")
def jesse_myers_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="Croesus_BTC",
        view_name="jesse-myers-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/willy-woo-heatmap/top-liked-tweets")
def willy_woo_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="willywoo",
        view_name="willy-woo-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/andy-edstrom-heatmap/top-liked-tweets")
def andy_edstrom_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="edstromandrew",
        view_name="andy-edstrom-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/dan-hillery-heatmap/top-liked-tweets")
def dan_hillery_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="hillery_dan",
        view_name="dan-hillery-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/adrian-morris-heatmap/top-liked-tweets")
def adrian_morris_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="_Adrian",
        view_name="adrian-morris-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/jeff-walton-heatmap/top-liked-tweets")
def jeff_walton_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="PunterJeff",
        view_name="jeff-walton-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/nithu-sezni-heatmap/top-liked-tweets")
def nithu_sezni_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="nithusezni",
        view_name="nithu-sezni-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/mason-heatmap/top-liked-tweets")
def mason_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="MasonFoard",
        view_name="mason-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/british-hodl-heatmap/top-liked-tweets")
def british_hodl_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="BritishHodl",
        view_name="british-hodl-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/lyn-alden-heatmap/top-liked-tweets")
def lyn_alden_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="LynAldenContact",
        view_name="lyn-alden-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/professor-b21-heatmap/top-liked-tweets")
def professor_b21_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="ProfessorB21",
        view_name="professor-b21-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/btc-gus-heatmap/top-liked-tweets")
def btc_gus_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="Scavacini777",
        view_name="btc-gus-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/bit-paine-heatmap/top-liked-tweets")
def bit_paine_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="BitPaine",
        view_name="bit-paine-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/matt-cole-heatmap/top-liked-tweets")
def matt_cole_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="ColeMacro",
        view_name="matt-cole-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/parker-lewis-heatmap/top-liked-tweets")
def parker_lewis_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="parkeralewis",
        view_name="parker-lewis-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/kristen-heatmap/top-liked-tweets")
def kristen_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="2dogs1chic",
        view_name="kristen-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/dana-in-hawaii-heatmap/top-liked-tweets")
def dana_in_hawaii_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="Danainhawaii",
        view_name="dana-in-hawaii-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/parabolic-code-heatmap/top-liked-tweets")
def parabolic_code_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="ParabolicCode",
        view_name="parabolic-code-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/bitquant-heatmap/top-liked-tweets")
def bitquant_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="BitQua",
        view_name="bitquant-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/ed-juline-heatmap/top-liked-tweets")
def ed_juline_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="ejuline",
        view_name="ed-juline-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/alex-thorn-heatmap/top-liked-tweets")
def alex_thorn_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="intangiblecoins",
        view_name="alex-thorn-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/btc-teacher-heatmap/top-liked-tweets")
def btc_teacher_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="BitcoinTeacher_",
        view_name="btc-teacher-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/roaring-ragnar-heatmap/top-liked-tweets")
def roaring_ragnar_heatmap_top_liked_tweets(
    phrase: str = Query(...),
    month_start: str = Query(...),
    limit: int = Query(default=3, ge=1, le=10),
) -> dict[str, object]:
    return _build_author_keyword_top_tweets(
        username="RoaringRagnar",
        view_name="roaring-ragnar-heatmap-top-liked-tweets",
        phrase=phrase,
        month_start=month_start,
        limit=limit,
    )


@router.get("/michael-sullivan-moods")
def michael_sullivan_moods(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
) -> dict[str, object]:
    return _build_overview_view(
        username="SullyMichaelvan",
        view_name="michael-sullivan-moods",
        granularity=granularity,
        analysis_start="2024-01-01T00:00:00Z",
    )


@router.get("/michael-sullivan-moods/mood-series")
def michael_sullivan_mood_series(
    granularity: str = Query(default="week", pattern="^(day|week)$"),
    model_key: str = Query(default=DEFAULT_MOOD_MODEL),
) -> dict[str, object]:
    return _build_author_moods(
        username="SullyMichaelvan",
        view_name="michael-sullivan-mood-series",
        granularity=granularity,
        model_key=model_key,
        analysis_start="2024-01-01T00:00:00Z",
    )


@router.get("/michael-sullivan-moods/btc-spot")
def michael_sullivan_moods_btc_spot() -> dict[str, object]:
    return _build_btc_spot_price()


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
