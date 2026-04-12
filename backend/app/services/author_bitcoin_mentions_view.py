from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re
from statistics import median

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.market_price_point import MarketPricePoint
from app.models.tweet import Tweet
from app.models.user import User
from app.services.market_data import floor_to_day


@dataclass(slots=True)
class AuthorBitcoinMentionsViewRequest:
    username: str
    phrase: str = "bitcoin"
    buy_amount_usd: float = 10.0
    view_name: str = "author-bitcoin-mentions"


@dataclass(slots=True)
class BitcoinMentionsLeaderboardRequest:
    usernames: list[str] | None = None
    phrase: str = "bitcoin"
    buy_amount_usd: float = 10.0
    view_name: str = "bitcoin-mentions-leaderboard"


def build_author_bitcoin_mentions_view(
    request: AuthorBitcoinMentionsViewRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    phrase = _normalize_phrase(request.phrase)
    _validate_buy_amount(request.buy_amount_usd)
    pattern, match_mode = _compile_phrase_pattern(phrase)

    session = session_factory()
    try:
        user = session.scalar(select(User).where(User.username == request.username))
        if user is None:
            raise RuntimeError(f"No canonical user found for username={request.username!r}.")

        price_map, latest_price_point = _load_btc_price_map(session)
        analysis = _analyze_user_mentions(
            session,
            user=user,
            phrase=phrase,
            pattern=pattern,
            buy_amount_usd=request.buy_amount_usd,
            price_map=price_map,
            latest_price_point=latest_price_point,
            include_mentions=True,
        )

        return {
            "view": request.view_name,
            "subject": {
                "platform_user_id": user.platform_user_id,
                "username": user.username,
                "display_name": user.display_name,
                "profile_image_url": user.profile_image_url,
            },
            "phrase": {
                "query": phrase,
                "match_mode": match_mode,
            },
            "pricing": _build_pricing_payload(latest_price_point),
            "btc_series": _build_btc_series(price_map),
            "summary": analysis["summary"],
            "cheapest_mentions": analysis["cheapest_mentions"],
            "latest_mentions": analysis["latest_mentions"],
            "mentions": analysis["mentions"],
        }
    finally:
        session.close()


def build_bitcoin_mentions_leaderboard(
    request: BitcoinMentionsLeaderboardRequest,
    *,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    phrase = _normalize_phrase(request.phrase)
    _validate_buy_amount(request.buy_amount_usd)
    pattern, match_mode = _compile_phrase_pattern(phrase)

    session = session_factory()
    try:
        price_map, latest_price_point = _load_btc_price_map(session)

        users_query = select(User).order_by(func.lower(User.username))
        if request.usernames:
            users_query = users_query.where(User.username.in_(request.usernames))
        users = list(session.scalars(users_query))
        if not users:
            raise RuntimeError("No canonical users were available for the Bitcoin mentions leaderboard.")

        leaderboard = []
        for user in users:
            analysis = _analyze_user_mentions(
                session,
                user=user,
                phrase=phrase,
                pattern=pattern,
                buy_amount_usd=request.buy_amount_usd,
                price_map=price_map,
                latest_price_point=latest_price_point,
                include_mentions=False,
            )
            leaderboard.append(
                {
                    "subject": {
                        "platform_user_id": user.platform_user_id,
                        "username": user.username,
                        "display_name": user.display_name,
                        "profile_image_url": user.profile_image_url,
                    },
                    **analysis["summary"],
                }
            )

        leaderboard.sort(
            key=lambda item: (
                item["average_entry_price_usd"] if item["average_entry_price_usd"] is not None else float("inf"),
                -item["mention_count"],
                item["subject"]["username"],
            )
        )

        return {
            "view": request.view_name,
            "phrase": {
                "query": phrase,
                "match_mode": match_mode,
            },
            "pricing": _build_pricing_payload(latest_price_point),
            "buy_amount_usd": request.buy_amount_usd,
            "leaderboard": leaderboard,
        }
    finally:
        session.close()


def _analyze_user_mentions(
    session: Session,
    *,
    user: User,
    phrase: str,
    pattern: re.Pattern[str],
    buy_amount_usd: float,
    price_map: dict[datetime, float],
    latest_price_point: tuple[datetime, float],
    include_mentions: bool,
) -> dict[str, object]:
    total_tweet_count = session.scalar(
        select(func.count(Tweet.id)).where(Tweet.author_user_id == user.id)
    )
    candidate_rows = session.execute(
        select(
            Tweet.platform_tweet_id,
            Tweet.url,
            Tweet.text,
            Tweet.created_at_platform,
            Tweet.like_count,
            Tweet.reply_count,
            Tweet.repost_count,
        )
        .where(
            Tweet.author_user_id == user.id,
            func.lower(Tweet.text).like(f"%{phrase.lower()}%"),
        )
        .order_by(Tweet.created_at_platform)
    ).all()

    latest_price_time, latest_price_usd = latest_price_point
    mentions: list[dict[str, object]] = []
    skipped_unpriced_mentions = 0
    for row in candidate_rows:
        if not pattern.search(row.text):
            continue

        price_day = floor_to_day(row.created_at_platform)
        btc_price_usd = price_map.get(price_day)
        if btc_price_usd is None:
            skipped_unpriced_mentions += 1
            continue

        btc_acquired = buy_amount_usd / btc_price_usd
        current_value_usd = btc_acquired * latest_price_usd
        mentions.append(
            {
                "platform_tweet_id": row.platform_tweet_id,
                "url": row.url,
                "text": row.text,
                "created_at_platform": _to_iso(row.created_at_platform),
                "pricing_day": _to_iso(price_day),
                "btc_price_usd": btc_price_usd,
                "hypothetical_buy_amount_usd": buy_amount_usd,
                "hypothetical_btc_acquired": btc_acquired,
                "hypothetical_current_value_usd": current_value_usd,
                "price_change_since_tweet_pct": ((latest_price_usd - btc_price_usd) / btc_price_usd) * 100,
                "like_count": row.like_count,
                "reply_count": row.reply_count,
                "repost_count": row.repost_count,
            }
        )

    mention_count = len(mentions)
    total_invested_usd = mention_count * buy_amount_usd
    total_btc_accumulated = sum(item["hypothetical_btc_acquired"] for item in mentions)
    current_value_usd = total_btc_accumulated * latest_price_usd
    total_return_usd = current_value_usd - total_invested_usd
    total_return_pct = (
        (total_return_usd / total_invested_usd) * 100 if total_invested_usd > 0 else None
    )
    mention_prices = [item["btc_price_usd"] for item in mentions]
    average_entry_price_usd = (
        total_invested_usd / total_btc_accumulated if total_btc_accumulated > 0 else None
    )

    cheapest_mentions = sorted(
        mentions,
        key=lambda item: (item["btc_price_usd"], item["created_at_platform"]),
    )[:8]
    latest_mentions = sorted(
        mentions,
        key=lambda item: item["created_at_platform"],
        reverse=True,
    )[:8]

    summary = {
        "total_tweet_count": total_tweet_count or 0,
        "candidate_tweet_count": len(candidate_rows),
        "mention_count": mention_count,
        "skipped_unpriced_mentions": skipped_unpriced_mentions,
        "buy_amount_usd": buy_amount_usd,
        "total_invested_usd": total_invested_usd,
        "total_btc_accumulated": total_btc_accumulated,
        "current_value_usd": current_value_usd,
        "total_return_usd": total_return_usd,
        "total_return_pct": total_return_pct,
        "average_entry_price_usd": average_entry_price_usd,
        "median_entry_price_usd": median(mention_prices) if mention_prices else None,
        "first_mention_at": mentions[0]["created_at_platform"] if mentions else None,
        "latest_mention_at": mentions[-1]["created_at_platform"] if mentions else None,
        "lowest_mention_price_usd": cheapest_mentions[0]["btc_price_usd"] if cheapest_mentions else None,
        "highest_mention_price_usd": max(mention_prices) if mention_prices else None,
        "best_timed_mention": cheapest_mentions[0] if cheapest_mentions else None,
        "worst_timed_mention": max(mentions, key=lambda item: item["btc_price_usd"]) if mentions else None,
        "current_btc_price_usd": latest_price_usd,
        "current_btc_price_as_of": _to_iso(latest_price_time),
    }

    return {
        "summary": summary,
        "cheapest_mentions": cheapest_mentions,
        "latest_mentions": latest_mentions,
        "mentions": mentions if include_mentions else [],
    }


def _load_btc_price_map(session: Session) -> tuple[dict[datetime, float], tuple[datetime, float]]:
    rows = session.execute(
        select(MarketPricePoint.observed_at, MarketPricePoint.price)
        .where(
            MarketPricePoint.asset_symbol == "BTC",
            MarketPricePoint.quote_currency == "USD",
            MarketPricePoint.interval == "day",
        )
        .order_by(MarketPricePoint.observed_at)
    ).all()
    if not rows:
        raise RuntimeError("No canonical BTC/USD daily price points were found.")

    price_map = {floor_to_day(observed_at): price for observed_at, price in rows}
    latest_observed_at, latest_price = rows[-1]
    return price_map, (latest_observed_at, latest_price)


def _build_pricing_payload(latest_price_point: tuple[datetime, float]) -> dict[str, object]:
    latest_observed_at, latest_price = latest_price_point
    return {
        "asset_symbol": "BTC",
        "quote_currency": "USD",
        "interval": "day",
        "methodology": (
            "Tweet timestamps are exact. BTC pricing uses the normalized UTC daily close for the "
            "tweet date because intraday candles are not stored in this project yet."
        ),
        "current_price_usd": latest_price,
        "current_price_as_of": _to_iso(latest_observed_at),
    }


def _build_btc_series(price_map: dict[datetime, float]) -> list[dict[str, object]]:
    return [
        {
            "timestamp": _to_iso(observed_at),
            "price_usd": price,
        }
        for observed_at, price in sorted(price_map.items())
    ]


def _compile_phrase_pattern(phrase: str) -> tuple[re.Pattern[str], str]:
    if re.search(r"\s", phrase):
        return re.compile(re.escape(phrase), re.IGNORECASE), "case_insensitive_phrase"
    return re.compile(rf"(?<!\w){re.escape(phrase)}(?!\w)", re.IGNORECASE), "case_insensitive_whole_word"


def _normalize_phrase(value: str) -> str:
    phrase = value.strip()
    if not phrase:
        raise RuntimeError("phrase must not be empty.")
    return phrase


def _validate_buy_amount(value: float) -> None:
    if value <= 0:
        raise RuntimeError("buy_amount_usd must be greater than 0.")


def _to_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
