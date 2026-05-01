from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import json
from math import sqrt
from pathlib import Path
import shutil
import sys
import time

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db.session import SessionLocal
from app.models.market_price_point import MarketPricePoint
from app.models.tweet import Tweet
from app.models.tweet_mood_score import TweetMoodScore
from app.models.user import User
from app.models.user_cohort_tag import UserCohortTag
from app.models.cohort_tag import CohortTag
from app.services.aggregate_mood_view import (
    _compute_weighted_moving_average,
    _mean,
    _population_stddev,
)
from app.services.market_data import floor_to_week
from app.services.moods import DEFAULT_MOOD_MODEL, DEFAULT_VISIBLE_MOOD_LABELS


@dataclass(slots=True)
class UserProfile:
    user_id: int
    platform_user_id: str
    username: str
    display_name: str | None


@dataclass(slots=True)
class CohortProfile:
    key: str
    label: str
    user_ids: set[int]
    kind: str


@dataclass(slots=True)
class EntityMetrics:
    entity_key: str
    entity_label: str
    entity_type: str
    mood_label: str
    current_score: float | None
    previous_score: float | None
    delta_1w: float | None
    prior_4w_average: float | None
    baseline_mean: float | None
    baseline_stddev: float | None
    baseline_week_count: int
    self_z_score: float | None
    scored_tweet_count_current: int
    current_aux_count: int
    series: list[float | None]


def log_progress(message: str) -> None:
    timestamp = datetime.now(UTC).strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find interesting dynamics across users, cohorts, moods, and BTC."
    )
    parser.add_argument(
        "--model-key",
        default=DEFAULT_MOOD_MODEL,
        help="Mood model key to analyze.",
    )
    parser.add_argument(
        "--analysis-start",
        default="2016-01-01T00:00:00Z",
        help="UTC ISO timestamp to begin analysis from.",
    )
    parser.add_argument(
        "--smoothing-window-weeks",
        type=int,
        default=8,
        help="Trailing weighted moving average window in weeks.",
    )
    parser.add_argument(
        "--baseline-window-weeks",
        type=int,
        default=52,
        help="Trailing baseline window in weeks.",
    )
    parser.add_argument(
        "--minimum-baseline-weeks",
        type=int,
        default=12,
        help="Minimum non-null baseline points required for self z-score.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=250,
        help="Maximum number of combined findings to keep.",
    )
    parser.add_argument(
        "--top-markdown-findings",
        type=int,
        default=40,
        help="How many findings to show in the markdown report top section.",
    )
    parser.add_argument(
        "--output-root",
        default=str(REPO_ROOT / "data" / "exports" / "dynamics-scout"),
        help="Directory where timestamped scout runs should be written.",
    )
    parser.add_argument(
        "--mood-label",
        action="append",
        dest="mood_labels",
        help="Optional mood label to analyze. Repeat to limit the scout to specific moods.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    started_at = time.perf_counter()
    generated_at = datetime.now(UTC)
    analysis_start = _parse_utc_datetime(args.analysis_start)
    output_root = Path(args.output_root).expanduser().resolve()
    run_slug = generated_at.strftime("%Y%m%d-%H%M%S")
    run_dir = output_root / run_slug
    mood_labels = tuple(
        label.strip().lower()
        for label in (args.mood_labels or DEFAULT_VISIBLE_MOOD_LABELS)
        if label and label.strip()
    )
    if not mood_labels:
        raise RuntimeError("Dynamics Scout requires at least one mood label.")
    log_progress(
        "Starting Dynamics Scout "
        f"for {len(mood_labels)} mood(s) from {analysis_start.isoformat().replace('+00:00', 'Z')}"
    )

    payload = build_dynamics_report(
        model_key=args.model_key,
        mood_labels=mood_labels,
        analysis_start=analysis_start,
        smoothing_window_weeks=args.smoothing_window_weeks,
        baseline_window_weeks=args.baseline_window_weeks,
        minimum_baseline_weeks=args.minimum_baseline_weeks,
        limit=args.limit,
        generated_at=generated_at,
    )
    markdown = render_markdown_report(
        payload=payload,
        top_markdown_findings=args.top_markdown_findings,
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / "summary.json"
    md_path = run_dir / "summary.md"
    latest_json_path = output_root / "latest.json"
    latest_md_path = output_root / "latest.md"

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    latest_json_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(json_path, latest_json_path)
    shutil.copyfile(md_path, latest_md_path)

    duration_seconds = time.perf_counter() - started_at
    log_progress(f"Wrote dynamics scout JSON to {json_path}")
    log_progress(f"Wrote dynamics scout Markdown to {md_path}")
    log_progress(f"Updated latest outputs in {output_root}")
    log_progress(f"Dynamics Scout finished in {duration_seconds:.2f}s")


def build_dynamics_report(
    *,
    model_key: str,
    mood_labels: tuple[str, ...],
    analysis_start: datetime,
    smoothing_window_weeks: int,
    baseline_window_weeks: int,
    minimum_baseline_weeks: int,
    limit: int,
    generated_at: datetime,
    session_factory: sessionmaker[Session] = SessionLocal,
) -> dict[str, object]:
    session = session_factory()
    try:
        log_progress("Querying mood rows from Postgres")
        mood_rows = session.execute(
            select(
                User.id,
                User.platform_user_id,
                User.username,
                User.display_name,
                Tweet.id,
                Tweet.created_at_platform,
                TweetMoodScore.mood_label,
                TweetMoodScore.score,
            )
            .join(Tweet, Tweet.author_user_id == User.id)
            .join(TweetMoodScore, TweetMoodScore.tweet_id == Tweet.id)
            .where(
                Tweet.created_at_platform >= analysis_start,
                TweetMoodScore.model_key == model_key,
                TweetMoodScore.status == "scored",
                TweetMoodScore.mood_label.in_(mood_labels),
            )
            .order_by(
                Tweet.created_at_platform.asc(),
                User.id.asc(),
                Tweet.id.asc(),
                TweetMoodScore.mood_label.asc(),
            )
        ).all()
        if not mood_rows:
            raise RuntimeError(f"No scored mood rows found for model_key={model_key!r}.")
        log_progress(f"Loaded {len(mood_rows):,} mood rows")

        log_progress("Building per-user weekly mood series")
        (
            ordered_weeks,
            user_profiles,
            user_values,
            user_weights,
            overall_tweet_count,
        ) = _build_user_weekly_series(mood_rows, mood_labels, analysis_start)
        log_progress(
            f"Built weekly user series across {len(ordered_weeks)} week(s) for "
            f"{len(user_profiles)} user(s)"
        )
        log_progress("Loading cohort memberships")
        cohort_memberships, cohorts = _load_cohorts(
            session,
            eligible_user_ids=set(user_profiles.keys()),
        )
        log_progress(f"Loaded {len(cohorts)} cohort scope(s)")
        log_progress("Building per-cohort weekly mood series")
        cohort_values, cohort_weights, cohort_tweet_counts = _build_cohort_weekly_series(
            ordered_weeks=ordered_weeks,
            mood_labels=mood_labels,
            user_values=user_values,
            user_weights=user_weights,
            cohorts=cohorts,
        )
        log_progress("Loading weekly BTC price series")
        btc_levels = _load_weekly_btc_levels(
            session,
            ordered_weeks=ordered_weeks,
        )
        btc_returns = _build_weekly_returns(btc_levels)
        log_progress("Computing smoothed user and cohort metrics")

        user_metrics_by_mood, user_current_stats_by_mood = _compute_entity_metrics(
            ordered_weeks=ordered_weeks,
            mood_labels=mood_labels,
            value_by_entity=user_values,
            weight_by_entity=user_weights,
            display_labels={user_id: _format_user_label(profile) for user_id, profile in user_profiles.items()},
            entity_type="user",
            smoothing_window_weeks=smoothing_window_weeks,
            baseline_window_weeks=baseline_window_weeks,
            minimum_baseline_weeks=minimum_baseline_weeks,
            current_count_lookup=user_weights,
        )
        cohort_metrics_by_mood, cohort_current_stats_by_mood = _compute_entity_metrics(
            ordered_weeks=ordered_weeks,
            mood_labels=mood_labels,
            value_by_entity=cohort_values,
            weight_by_entity=cohort_weights,
            display_labels={cohort.key: cohort.label for cohort in cohorts.values()},
            entity_type="cohort",
            smoothing_window_weeks=smoothing_window_weeks,
            baseline_window_weeks=baseline_window_weeks,
            minimum_baseline_weeks=minimum_baseline_weeks,
            current_count_lookup=cohort_tweet_counts,
        )

        log_progress("Scoring findings across signal families")
        findings: list[dict[str, object]] = []
        findings.extend(
            _build_user_outlier_findings(
                user_metrics_by_mood=user_metrics_by_mood,
                user_current_stats_by_mood=user_current_stats_by_mood,
                user_profiles=user_profiles,
            )
        )
        findings.extend(
            _build_cohort_outlier_findings(
                cohort_metrics_by_mood=cohort_metrics_by_mood,
                cohort_current_stats_by_mood=cohort_current_stats_by_mood,
            )
        )
        findings.extend(
            _build_cohort_vs_cohort_findings(
                cohort_metrics_by_mood=cohort_metrics_by_mood,
                cohorts=cohorts,
            )
        )
        findings.extend(
            _build_user_vs_cohort_findings(
                user_metrics_by_mood=user_metrics_by_mood,
                user_profiles=user_profiles,
                cohort_memberships=cohort_memberships,
                cohort_metrics_by_mood=cohort_metrics_by_mood,
                user_current_scores_by_mood=user_current_stats_by_mood,
                cohorts=cohorts,
            )
        )
        findings.extend(
            _build_btc_relationship_findings(
                metrics_by_mood=user_metrics_by_mood,
                btc_levels=btc_levels,
                btc_returns=btc_returns,
            )
        )
        findings.extend(
            _build_btc_relationship_findings(
                metrics_by_mood=cohort_metrics_by_mood,
                btc_levels=btc_levels,
                btc_returns=btc_returns,
            )
        )
        findings.extend(
            _build_regime_shift_findings(
                metrics_by_mood=user_metrics_by_mood,
            )
        )
        findings.extend(
            _build_regime_shift_findings(
                metrics_by_mood=cohort_metrics_by_mood,
            )
        )

        findings.sort(key=lambda finding: float(finding["interestingness_score"]), reverse=True)
        findings = findings[:limit]
        for index, finding in enumerate(findings, start=1):
            finding["rank"] = index

        type_counts = Counter(str(finding["finding_type"]) for finding in findings)
        mood_counts = Counter(
            str(finding["mood_label"])
            for finding in findings
            if finding.get("mood_label") is not None
        )

        return {
            "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
            "inputs": {
                "model_key": model_key,
                "analysis_start": analysis_start.isoformat().replace("+00:00", "Z"),
                "smoothing_window_weeks": smoothing_window_weeks,
                "baseline_window_weeks": baseline_window_weeks,
                "minimum_baseline_weeks": minimum_baseline_weeks,
                "mood_labels": list(mood_labels),
            },
            "summary": {
                "week_count": len(ordered_weeks),
                "range_start": ordered_weeks[0].isoformat().replace("+00:00", "Z"),
                "range_end": ordered_weeks[-1].isoformat().replace("+00:00", "Z"),
                "eligible_user_count": len(user_profiles),
                "cohort_count": len(cohorts),
                "scored_tweet_count": overall_tweet_count,
                "finding_count": len(findings),
                "finding_type_counts": dict(type_counts),
                "mood_counts": dict(mood_counts.most_common()),
            },
            "findings": findings,
        }
    finally:
        session.close()


def render_markdown_report(
    *,
    payload: dict[str, object],
    top_markdown_findings: int,
) -> str:
    summary = payload["summary"]
    findings: list[dict[str, object]] = payload["findings"]
    finding_type_counts = summary["finding_type_counts"]
    lines = [
        "# Dynamics Scout",
        "",
        f"- Generated: {payload['generated_at']}",
        f"- Range: {summary['range_start']} to {summary['range_end']}",
        f"- Eligible users: {summary['eligible_user_count']}",
        f"- Cohorts: {summary['cohort_count']}",
        f"- Scored tweets: {summary['scored_tweet_count']}",
        f"- Findings retained: {summary['finding_count']}",
        "",
        "## Top Findings",
        "",
    ]
    for finding in findings[:top_markdown_findings]:
        lines.append(
            f"{finding['rank']}. [{finding['interestingness_score']:.2f}] {finding['headline']}"
        )
        lines.append(f"   - {finding['short_story']}")
    lines.extend(["", "## Finding Type Counts", ""])
    for finding_type, count in sorted(
        finding_type_counts.items(),
        key=lambda item: item[1],
        reverse=True,
    ):
        lines.append(f"- {finding_type}: {count}")

    findings_by_type: dict[str, list[dict[str, object]]] = defaultdict(list)
    for finding in findings:
        findings_by_type[str(finding["finding_type"])].append(finding)

    lines.extend(["", "## Top Findings By Type", ""])
    for finding_type, typed_findings in sorted(
        findings_by_type.items(),
        key=lambda item: item[0],
    ):
        lines.append(f"### {finding_type}")
        lines.append("")
        for finding in typed_findings[:5]:
            lines.append(
                f"- [{finding['interestingness_score']:.2f}] {finding['headline']} :: {finding['short_story']}"
            )
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _build_user_weekly_series(
    rows: list[tuple[object, ...]],
    mood_labels: tuple[str, ...],
    analysis_start: datetime,
) -> tuple[
    list[datetime],
    dict[int, UserProfile],
    dict[int, dict[str, list[float | None]]],
    dict[int, dict[str, list[int]]],
    int,
]:
    user_profiles: dict[int, UserProfile] = {}
    week_user_moods: dict[datetime, dict[int, dict[str, dict[str, float | int]]]] = {}
    sorted_weeks: list[datetime] = []
    seen_weeks: set[datetime] = set()
    overall_tweet_ids: set[int] = set()

    for user_id, platform_user_id, username, display_name, tweet_id, created_at, mood_label, score in rows:
        normalized_user_id = int(user_id)
        user_profiles.setdefault(
            normalized_user_id,
            UserProfile(
                user_id=normalized_user_id,
                platform_user_id=str(platform_user_id),
                username=str(username),
                display_name=str(display_name) if display_name is not None else None,
            ),
        )

        bucket_start = floor_to_week(created_at.astimezone(UTC))
        if bucket_start not in seen_weeks:
            seen_weeks.add(bucket_start)
            sorted_weeks.append(bucket_start)

        week_users = week_user_moods.setdefault(bucket_start, {})
        user_bucket = week_users.setdefault(
            normalized_user_id,
            {
                label: {"sum_score": 0.0, "score_count": 0}
                for label in mood_labels
            },
        )
        mood_bucket = user_bucket[str(mood_label)]
        mood_bucket["sum_score"] += float(score)
        mood_bucket["score_count"] += 1
        overall_tweet_ids.add(int(tweet_id))

    sorted_weeks.sort()
    full_weeks: list[datetime] = []
    current = floor_to_week(analysis_start.astimezone(UTC))
    end = sorted_weeks[-1]
    while current <= end:
        full_weeks.append(current)
        current += timedelta(days=7)

    week_index_by_start = {week_start: index for index, week_start in enumerate(full_weeks)}
    week_count = len(full_weeks)
    user_values: dict[int, dict[str, list[float | None]]] = {
        user_id: {mood_label: [None] * week_count for mood_label in mood_labels}
        for user_id in user_profiles
    }
    user_weights: dict[int, dict[str, list[int]]] = {
        user_id: {mood_label: [0] * week_count for mood_label in mood_labels}
        for user_id in user_profiles
    }

    for week_start, week_users in week_user_moods.items():
        week_index = week_index_by_start[week_start]
        for user_id, mood_map in week_users.items():
            for mood_label in mood_labels:
                score_count = int(mood_map[mood_label]["score_count"])
                if score_count <= 0:
                    continue
                user_values[user_id][mood_label][week_index] = (
                    float(mood_map[mood_label]["sum_score"]) / score_count
                )
                user_weights[user_id][mood_label][week_index] = score_count

    return full_weeks, user_profiles, user_values, user_weights, len(overall_tweet_ids)


def _load_cohorts(
    session: Session,
    *,
    eligible_user_ids: set[int],
) -> tuple[dict[int, list[str]], dict[str, CohortProfile]]:
    membership_rows = session.execute(
        select(UserCohortTag.user_id, CohortTag.slug, CohortTag.name)
        .join(CohortTag, CohortTag.id == UserCohortTag.cohort_tag_id)
        .where(UserCohortTag.user_id.in_(eligible_user_ids))
        .order_by(CohortTag.slug.asc(), UserCohortTag.user_id.asc())
    ).all()

    cohort_memberships: dict[int, list[str]] = {user_id: [] for user_id in eligible_user_ids}
    cohorts: dict[str, CohortProfile] = {
        "all": CohortProfile(
            key="all",
            label="All tracked users",
            user_ids=set(eligible_user_ids),
            kind="all",
        )
    }
    for user_id, slug, name in membership_rows:
        normalized_user_id = int(user_id)
        normalized_slug = str(slug)
        cohort_memberships.setdefault(normalized_user_id, []).append(normalized_slug)
        cohort = cohorts.setdefault(
            normalized_slug,
            CohortProfile(
                key=normalized_slug,
                label=str(name),
                user_ids=set(),
                kind="tag",
            ),
        )
        cohort.user_ids.add(normalized_user_id)

    return cohort_memberships, cohorts


def _build_cohort_weekly_series(
    *,
    ordered_weeks: list[datetime],
    mood_labels: tuple[str, ...],
    user_values: dict[int, dict[str, list[float | None]]],
    user_weights: dict[int, dict[str, list[int]]],
    cohorts: dict[str, CohortProfile],
) -> tuple[
    dict[str, dict[str, list[float | None]]],
    dict[str, dict[str, list[int]]],
    dict[str, dict[str, list[int]]],
]:
    week_count = len(ordered_weeks)
    cohort_values: dict[str, dict[str, list[float | None]]] = {
        cohort_key: {mood_label: [None] * week_count for mood_label in mood_labels}
        for cohort_key in cohorts
    }
    cohort_weights: dict[str, dict[str, list[int]]] = {
        cohort_key: {mood_label: [0] * week_count for mood_label in mood_labels}
        for cohort_key in cohorts
    }
    cohort_tweet_counts: dict[str, dict[str, list[int]]] = {
        cohort_key: {mood_label: [0] * week_count for mood_label in mood_labels}
        for cohort_key in cohorts
    }

    for cohort_key, cohort in cohorts.items():
        for mood_label in mood_labels:
            for week_index in range(week_count):
                value_sum = 0.0
                active_user_count = 0
                tweet_count = 0
                for user_id in cohort.user_ids:
                    user_value = user_values[user_id][mood_label][week_index]
                    if user_value is None:
                        continue
                    value_sum += user_value
                    active_user_count += 1
                    tweet_count += user_weights[user_id][mood_label][week_index]
                if active_user_count > 0:
                    cohort_values[cohort_key][mood_label][week_index] = value_sum / active_user_count
                    cohort_weights[cohort_key][mood_label][week_index] = active_user_count
                    cohort_tweet_counts[cohort_key][mood_label][week_index] = tweet_count

    return cohort_values, cohort_weights, cohort_tweet_counts


def _load_weekly_btc_levels(
    session: Session,
    *,
    ordered_weeks: list[datetime],
) -> list[float | None]:
    range_start = ordered_weeks[0]
    range_end = ordered_weeks[-1] + timedelta(days=7)
    rows = session.execute(
        select(MarketPricePoint.observed_at, MarketPricePoint.price)
        .where(
            MarketPricePoint.asset_symbol == "BTC",
            MarketPricePoint.quote_currency == "USD",
            MarketPricePoint.interval == "day",
            MarketPricePoint.observed_at >= range_start,
            MarketPricePoint.observed_at < range_end,
        )
        .order_by(MarketPricePoint.observed_at.asc())
    ).all()
    weekly_last_price: dict[datetime, float] = {}
    for observed_at, price in rows:
        weekly_last_price[floor_to_week(observed_at.astimezone(UTC))] = float(price)

    levels: list[float | None] = []
    previous_price: float | None = None
    for week_start in ordered_weeks:
        current_price = weekly_last_price.get(week_start, previous_price)
        levels.append(current_price)
        if current_price is not None:
            previous_price = current_price
    return levels


def _build_weekly_returns(levels: list[float | None]) -> list[float | None]:
    returns: list[float | None] = [None]
    for index in range(1, len(levels)):
        current = levels[index]
        previous = levels[index - 1]
        if current is None or previous in (None, 0):
            returns.append(None)
            continue
        returns.append((current / previous) - 1.0)
    return returns


def _compute_entity_metrics(
    *,
    ordered_weeks: list[datetime],
    mood_labels: tuple[str, ...],
    value_by_entity: dict[object, dict[str, list[float | None]]],
    weight_by_entity: dict[object, dict[str, list[int]]],
    display_labels: dict[object, str],
    entity_type: str,
    smoothing_window_weeks: int,
    baseline_window_weeks: int,
    minimum_baseline_weeks: int,
    current_count_lookup: dict[object, dict[str, list[int]]],
) -> tuple[dict[str, dict[object, EntityMetrics]], dict[str, dict[str, float | None]]]:
    metrics_by_mood: dict[str, dict[object, EntityMetrics]] = {mood_label: {} for mood_label in mood_labels}
    current_stats_by_mood: dict[str, dict[str, float | None]] = {}

    total_moods = len(mood_labels)
    for mood_index, mood_label in enumerate(mood_labels, start=1):
        log_progress(
            f"Computing {entity_type} metrics for mood {mood_index}/{total_moods}: "
            f"{format_mood_label(mood_label)}"
        )
        current_scores: list[float] = []
        pending_metrics: list[EntityMetrics] = []
        for entity_key, values_by_mood in value_by_entity.items():
            series = values_by_mood[mood_label]
            weights = weight_by_entity[entity_key][mood_label]
            smoothed = _compute_weighted_moving_average(
                values=series,
                weights=weights,
                window_size=smoothing_window_weeks,
            )
            current_score = smoothed[-1] if smoothed else None
            if current_score is None:
                continue
            previous_score = smoothed[-2] if len(smoothed) > 1 else None
            delta_1w = (
                current_score - previous_score
                if previous_score is not None
                else None
            )
            baseline_values = [value for value in smoothed[:-1] if value is not None]
            baseline_tail = baseline_values[-baseline_window_weeks:]
            baseline_mean = _mean(baseline_tail) if baseline_tail else None
            baseline_stddev = _population_stddev(baseline_tail) if baseline_tail else None
            self_z_score = None
            if (
                baseline_mean is not None
                and baseline_stddev is not None
                and len(baseline_tail) >= minimum_baseline_weeks
                and baseline_stddev > 0
            ):
                self_z_score = (current_score - baseline_mean) / baseline_stddev
            prior_4w_values = [value for value in smoothed[-5:-1] if value is not None]
            prior_4w_average = _mean(prior_4w_values) if prior_4w_values else None
            metrics = EntityMetrics(
                entity_key=str(entity_key),
                entity_label=display_labels[entity_key],
                entity_type=entity_type,
                mood_label=mood_label,
                current_score=current_score,
                previous_score=previous_score,
                delta_1w=delta_1w,
                prior_4w_average=prior_4w_average,
                baseline_mean=baseline_mean,
                baseline_stddev=baseline_stddev,
                baseline_week_count=len(baseline_tail),
                self_z_score=self_z_score,
                scored_tweet_count_current=current_count_lookup[entity_key][mood_label][-1],
                current_aux_count=weights[-1] if weights else 0,
                series=smoothed,
            )
            pending_metrics.append(metrics)
            current_scores.append(current_score)

        current_mean = _mean(current_scores) if current_scores else None
        current_stddev = _population_stddev(current_scores) if current_scores else None
        current_stats_by_mood[mood_label] = {
            "mean": current_mean,
            "stddev": current_stddev,
        }
        for metrics in pending_metrics:
            metrics_by_mood[mood_label][metrics.entity_key] = metrics

    return metrics_by_mood, current_stats_by_mood


def _build_user_outlier_findings(
    *,
    user_metrics_by_mood: dict[str, dict[object, EntityMetrics]],
    user_current_stats_by_mood: dict[str, dict[str, float | None]],
    user_profiles: dict[int, UserProfile],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for mood_label, metrics_by_user in user_metrics_by_mood.items():
        current_mean = user_current_stats_by_mood[mood_label]["mean"]
        current_stddev = user_current_stats_by_mood[mood_label]["stddev"]
        for entity_key, metrics in metrics_by_user.items():
            if metrics.self_z_score is None or metrics.current_score is None:
                continue
            cohort_z_score = None
            if current_mean is not None and current_stddev is not None and current_stddev > 0:
                cohort_z_score = (metrics.current_score - current_mean) / current_stddev
            direction = "above" if metrics.self_z_score >= 0 else "below"
            score = (
                abs(metrics.self_z_score) * 3.2
                + abs(cohort_z_score or 0.0) * 2.0
                + abs(metrics.delta_1w or 0.0) * 30.0
            )
            findings.append(
                _make_finding(
                    finding_type="user_mood_outlier",
                    entity_type="user",
                    entity_name=metrics.entity_label,
                    mood_label=mood_label,
                    interestingness_score=score,
                    headline=(
                        f"{metrics.entity_label} shows {format_mood_label(mood_label)} "
                        f"{direction} personal baseline"
                    ),
                    short_story=(
                        f"{metrics.entity_label} is {metrics.self_z_score:+.2f} sigma versus "
                        f"personal baseline, {cohort_z_score:+.2f} sigma versus the user set, "
                        f"and moved {metrics.delta_1w:+.3f} over the last week."
                        if cohort_z_score is not None and metrics.delta_1w is not None
                        else f"{metrics.entity_label} is {metrics.self_z_score:+.2f} sigma "
                        f"versus personal baseline."
                    ),
                    metrics={
                        "current_score": metrics.current_score,
                        "self_z_score": metrics.self_z_score,
                        "cohort_z_score": cohort_z_score,
                        "delta_1w": metrics.delta_1w,
                        "baseline_mean": metrics.baseline_mean,
                        "baseline_stddev": metrics.baseline_stddev,
                        "baseline_week_count": metrics.baseline_week_count,
                        "scored_tweet_count_current": metrics.scored_tweet_count_current,
                        "username": user_profiles[int(entity_key)].username,
                    },
                )
            )
    return findings


def _build_cohort_outlier_findings(
    *,
    cohort_metrics_by_mood: dict[str, dict[object, EntityMetrics]],
    cohort_current_stats_by_mood: dict[str, dict[str, float | None]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for mood_label, metrics_by_cohort in cohort_metrics_by_mood.items():
        current_mean = cohort_current_stats_by_mood[mood_label]["mean"]
        current_stddev = cohort_current_stats_by_mood[mood_label]["stddev"]
        for metrics in metrics_by_cohort.values():
            if metrics.entity_key == "all" or metrics.self_z_score is None or metrics.current_score is None:
                continue
            cohort_z_score = None
            if current_mean is not None and current_stddev is not None and current_stddev > 0:
                cohort_z_score = (metrics.current_score - current_mean) / current_stddev
            direction = "above" if metrics.self_z_score >= 0 else "below"
            score = (
                abs(metrics.self_z_score) * 3.0
                + abs(cohort_z_score or 0.0) * 2.0
                + abs(metrics.delta_1w or 0.0) * 28.0
            )
            findings.append(
                _make_finding(
                    finding_type="cohort_mood_outlier",
                    entity_type="cohort",
                    entity_name=metrics.entity_label,
                    mood_label=mood_label,
                    interestingness_score=score,
                    headline=(
                        f"{metrics.entity_label} shows {format_mood_label(mood_label)} "
                        f"{direction} its own trailing baseline"
                    ),
                    short_story=(
                        f"{metrics.entity_label} is {metrics.self_z_score:+.2f} sigma versus "
                        f"its trailing baseline and moved {metrics.delta_1w:+.3f} last week."
                    ),
                    metrics={
                        "current_score": metrics.current_score,
                        "self_z_score": metrics.self_z_score,
                        "cohort_z_score": cohort_z_score,
                        "delta_1w": metrics.delta_1w,
                        "baseline_mean": metrics.baseline_mean,
                        "baseline_stddev": metrics.baseline_stddev,
                        "baseline_week_count": metrics.baseline_week_count,
                        "scored_tweet_count_current": metrics.scored_tweet_count_current,
                    },
                )
            )
    return findings


def _build_cohort_vs_cohort_findings(
    *,
    cohort_metrics_by_mood: dict[str, dict[object, EntityMetrics]],
    cohorts: dict[str, CohortProfile],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    cohort_keys = sorted(cohorts.keys())
    for mood_label, metrics_by_cohort in cohort_metrics_by_mood.items():
        for left_index, left_key in enumerate(cohort_keys):
            left_metrics = metrics_by_cohort.get(left_key)
            if left_metrics is None or left_metrics.current_score is None:
                continue
            for right_key in cohort_keys[left_index + 1 :]:
                right_metrics = metrics_by_cohort.get(right_key)
                if right_metrics is None or right_metrics.current_score is None:
                    continue
                current_gap = left_metrics.current_score - right_metrics.current_score
                delta_gap = (
                    (left_metrics.delta_1w or 0.0) - (right_metrics.delta_1w or 0.0)
                    if left_metrics.delta_1w is not None and right_metrics.delta_1w is not None
                    else None
                )
                score = abs(current_gap) * 45.0 + abs(delta_gap or 0.0) * 18.0
                findings.append(
                    _make_finding(
                        finding_type="cohort_vs_cohort_divergence",
                        entity_type="cohort-pair",
                        entity_name=f"{left_metrics.entity_label} vs {right_metrics.entity_label}",
                        mood_label=mood_label,
                        interestingness_score=score,
                        headline=(
                            f"{left_metrics.entity_label} and {right_metrics.entity_label} diverge on "
                            f"{format_mood_label(mood_label)}"
                        ),
                        short_story=(
                            f"Current gap is {current_gap:+.3f}"
                            + (
                                f" with a weekly change gap of {delta_gap:+.3f}."
                                if delta_gap is not None
                                else "."
                            )
                        ),
                        metrics={
                            "left_current_score": left_metrics.current_score,
                            "right_current_score": right_metrics.current_score,
                            "current_gap": current_gap,
                            "left_delta_1w": left_metrics.delta_1w,
                            "right_delta_1w": right_metrics.delta_1w,
                            "delta_gap": delta_gap,
                            "left_cohort_key": left_key,
                            "right_cohort_key": right_key,
                        },
                    )
                )
    return findings


def _build_user_vs_cohort_findings(
    *,
    user_metrics_by_mood: dict[str, dict[object, EntityMetrics]],
    user_profiles: dict[int, UserProfile],
    cohort_memberships: dict[int, list[str]],
    cohort_metrics_by_mood: dict[str, dict[object, EntityMetrics]],
    user_current_scores_by_mood: dict[str, dict[str, float | None]],
    cohorts: dict[str, CohortProfile],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    current_user_series_by_mood: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for mood_label, metrics_by_user in user_metrics_by_mood.items():
        for metrics in metrics_by_user.values():
            if metrics.current_score is None:
                continue
            current_user_series_by_mood[mood_label]["all"].append(metrics.current_score)
            user_id = int(metrics.entity_key)
            for cohort_key in cohort_memberships.get(user_id, []):
                current_user_series_by_mood[mood_label][cohort_key].append(metrics.current_score)

    for mood_label, metrics_by_user in user_metrics_by_mood.items():
        for metrics in metrics_by_user.values():
            if metrics.current_score is None:
                continue
            user_id = int(metrics.entity_key)
            comparison_cohorts = ["all", *cohort_memberships.get(user_id, [])]
            for cohort_key in comparison_cohorts:
                cohort_metrics = cohort_metrics_by_mood[mood_label].get(cohort_key)
                if cohort_metrics is None or cohort_metrics.current_score is None:
                    continue
                comparison_scores = current_user_series_by_mood[mood_label].get(cohort_key, [])
                current_stddev = _population_stddev(comparison_scores) if comparison_scores else None
                divergence_z = None
                if current_stddev is not None and current_stddev > 0:
                    divergence_z = (metrics.current_score - cohort_metrics.current_score) / current_stddev
                current_gap = metrics.current_score - cohort_metrics.current_score
                score = abs(divergence_z or 0.0) * 3.0 + abs(current_gap) * 40.0
                if score <= 0:
                    continue
                findings.append(
                    _make_finding(
                        finding_type="user_vs_cohort_divergence",
                        entity_type="user-vs-cohort",
                        entity_name=f"{metrics.entity_label} vs {cohort_metrics.entity_label}",
                        mood_label=mood_label,
                        interestingness_score=score,
                        headline=(
                            f"{metrics.entity_label} diverges from {cohort_metrics.entity_label} on "
                            f"{format_mood_label(mood_label)}"
                        ),
                        short_story=(
                            f"Current gap is {current_gap:+.3f}"
                            + (
                                f", or {divergence_z:+.2f} sigma relative to that comparison set."
                                if divergence_z is not None
                                else "."
                            )
                        ),
                        metrics={
                            "user_current_score": metrics.current_score,
                            "comparison_current_score": cohort_metrics.current_score,
                            "current_gap": current_gap,
                            "divergence_z_score": divergence_z,
                            "comparison_key": cohort_key,
                            "comparison_label": cohort_metrics.entity_label,
                            "username": user_profiles[user_id].username,
                            "comparison_user_count": len(cohorts[cohort_key].user_ids),
                        },
                    )
                )
    return findings


def _build_btc_relationship_findings(
    *,
    metrics_by_mood: dict[str, dict[object, EntityMetrics]],
    btc_levels: list[float | None],
    btc_returns: list[float | None],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for mood_label, metrics_by_entity in metrics_by_mood.items():
        for metrics in metrics_by_entity.values():
            level_corr_8w = _pearson_recent(metrics.series, btc_levels, window_size=8, min_pairs=6)
            level_corr_52w = _pearson_recent(metrics.series, btc_levels, window_size=52, min_pairs=12)
            return_corr_8w = _pearson_recent(metrics.series, btc_returns, window_size=8, min_pairs=6)
            return_corr_52w = _pearson_recent(metrics.series, btc_returns, window_size=52, min_pairs=12)
            lead_corr_8w = _pearson_recent_lead(metrics.series, btc_returns, window_size=8, min_pairs=5)
            lead_corr_52w = _pearson_recent_lead(metrics.series, btc_returns, window_size=52, min_pairs=10)

            best_level_corr, best_level_window = _pick_best_window(level_corr_8w, level_corr_52w)
            if best_level_corr is not None:
                findings.append(
                    _make_finding(
                        finding_type="btc_level_correlation",
                        entity_type=metrics.entity_type,
                        entity_name=metrics.entity_label,
                        mood_label=mood_label,
                        interestingness_score=abs(best_level_corr) * 12.0,
                        headline=(
                            f"{metrics.entity_label} has strong {format_mood_label(mood_label)} "
                            f"relationship with BTC price level"
                        ),
                        short_story=(
                            f"Best BTC level correlation is {best_level_corr:+.2f} over the trailing "
                            f"{best_level_window}-week window."
                        ),
                        metrics={
                            "level_corr_8w": level_corr_8w,
                            "level_corr_52w": level_corr_52w,
                            "best_level_corr": best_level_corr,
                            "best_level_window": best_level_window,
                        },
                    )
                )

            best_return_corr, best_return_window = _pick_best_window(return_corr_8w, return_corr_52w)
            if best_return_corr is not None:
                findings.append(
                    _make_finding(
                        finding_type="btc_return_correlation",
                        entity_type=metrics.entity_type,
                        entity_name=metrics.entity_label,
                        mood_label=mood_label,
                        interestingness_score=abs(best_return_corr) * 12.5,
                        headline=(
                            f"{metrics.entity_label} tracks BTC returns through "
                            f"{format_mood_label(mood_label)}"
                        ),
                        short_story=(
                            f"Best BTC return correlation is {best_return_corr:+.2f} over the trailing "
                            f"{best_return_window}-week window."
                        ),
                        metrics={
                            "return_corr_8w": return_corr_8w,
                            "return_corr_52w": return_corr_52w,
                            "best_return_corr": best_return_corr,
                            "best_return_window": best_return_window,
                        },
                    )
                )

            if (
                level_corr_8w is not None
                and level_corr_52w is not None
                and abs(level_corr_8w - level_corr_52w) > 0
            ):
                findings.append(
                    _make_finding(
                        finding_type="btc_decoupling",
                        entity_type=metrics.entity_type,
                        entity_name=metrics.entity_label,
                        mood_label=mood_label,
                        interestingness_score=abs(level_corr_8w - level_corr_52w) * 14.0,
                        headline=(
                            f"{metrics.entity_label} recently changed its BTC linkage on "
                            f"{format_mood_label(mood_label)}"
                        ),
                        short_story=(
                            f"BTC level correlation shifted from {level_corr_52w:+.2f} over 52 weeks "
                            f"to {level_corr_8w:+.2f} over 8 weeks."
                        ),
                        metrics={
                            "level_corr_8w": level_corr_8w,
                            "level_corr_52w": level_corr_52w,
                            "correlation_shift": level_corr_8w - level_corr_52w,
                        },
                    )
                )

            best_lead_corr, best_lead_window = _pick_best_window(lead_corr_8w, lead_corr_52w)
            if best_lead_corr is not None:
                findings.append(
                    _make_finding(
                        finding_type="btc_lead_lag_signal",
                        entity_type=metrics.entity_type,
                        entity_name=metrics.entity_label,
                        mood_label=mood_label,
                        interestingness_score=abs(best_lead_corr) * 12.0,
                        headline=(
                            f"{metrics.entity_label} may lead BTC moves through "
                            f"{format_mood_label(mood_label)}"
                        ),
                        short_story=(
                            f"Lead correlation to next-week BTC returns is {best_lead_corr:+.2f} "
                            f"over the trailing {best_lead_window}-week window."
                        ),
                        metrics={
                            "lead_corr_8w": lead_corr_8w,
                            "lead_corr_52w": lead_corr_52w,
                            "best_lead_corr": best_lead_corr,
                            "best_lead_window": best_lead_window,
                        },
                    )
                )
    return findings


def _build_regime_shift_findings(
    *,
    metrics_by_mood: dict[str, dict[object, EntityMetrics]],
) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []
    for mood_label, metrics_by_entity in metrics_by_mood.items():
        for metrics in metrics_by_entity.values():
            if metrics.current_score is None:
                continue
            prior_4w_average = metrics.prior_4w_average
            if prior_4w_average is None:
                continue
            current_gap = metrics.current_score - prior_4w_average
            sign_flip = prior_4w_average * metrics.current_score < 0
            score = abs(metrics.delta_1w or 0.0) * 32.0 + abs(current_gap) * 24.0 + (3.0 if sign_flip else 0.0)
            findings.append(
                _make_finding(
                    finding_type="regime_shift",
                    entity_type=metrics.entity_type,
                    entity_name=metrics.entity_label,
                    mood_label=mood_label,
                    interestingness_score=score,
                    headline=(
                        f"{metrics.entity_label} may be in a {format_mood_label(mood_label)} regime shift"
                    ),
                    short_story=(
                        f"Current reading is {current_gap:+.3f} away from its prior four-week average "
                        f"with a one-week move of {metrics.delta_1w:+.3f}."
                    ),
                    metrics={
                        "current_score": metrics.current_score,
                        "prior_4w_average": prior_4w_average,
                        "current_gap_vs_prior_4w": current_gap,
                        "delta_1w": metrics.delta_1w,
                        "sign_flip": sign_flip,
                    },
                )
            )
    return findings


def _make_finding(
    *,
    finding_type: str,
    entity_type: str,
    entity_name: str,
    mood_label: str | None,
    interestingness_score: float,
    headline: str,
    short_story: str,
    metrics: dict[str, object],
) -> dict[str, object]:
    return {
        "finding_type": finding_type,
        "entity_type": entity_type,
        "entity_name": entity_name,
        "mood_label": mood_label,
        "interestingness_score": round(float(interestingness_score), 4),
        "headline": headline,
        "short_story": short_story,
        "metrics": metrics,
    }


def _pick_best_window(short_window: float | None, long_window: float | None) -> tuple[float | None, int | None]:
    if short_window is None and long_window is None:
        return None, None
    if short_window is None:
        return long_window, 52
    if long_window is None:
        return short_window, 8
    return (short_window, 8) if abs(short_window) >= abs(long_window) else (long_window, 52)


def _pearson_recent(
    series_a: list[float | None],
    series_b: list[float | None],
    *,
    window_size: int,
    min_pairs: int,
) -> float | None:
    return _pearson(series_a[-window_size:], series_b[-window_size:], min_pairs=min_pairs)


def _pearson_recent_lead(
    series_a: list[float | None],
    series_b: list[float | None],
    *,
    window_size: int,
    min_pairs: int,
) -> float | None:
    if window_size <= 1:
        return None
    return _pearson(series_a[-window_size:-1], series_b[-window_size + 1 :], min_pairs=min_pairs)


def _pearson(
    series_a: list[float | None],
    series_b: list[float | None],
    *,
    min_pairs: int,
) -> float | None:
    paired = [
        (left, right)
        for left, right in zip(series_a, series_b, strict=False)
        if left is not None and right is not None
    ]
    if len(paired) < min_pairs:
        return None
    left_values = [left for left, _right in paired]
    right_values = [right for _left, right in paired]
    left_mean = _mean(left_values)
    right_mean = _mean(right_values)
    if left_mean is None or right_mean is None:
        return None
    numerator = sum(
        (left - left_mean) * (right - right_mean)
        for left, right in paired
    )
    left_variance = sum((left - left_mean) ** 2 for left in left_values)
    right_variance = sum((right - right_mean) ** 2 for right in right_values)
    denominator = sqrt(left_variance * right_variance)
    if denominator <= 0:
        return None
    return numerator / denominator


def _format_user_label(profile: UserProfile) -> str:
    if profile.display_name:
        return f"{profile.display_name} (@{profile.username})"
    return f"@{profile.username}"


def format_mood_label(value: str) -> str:
    return " ".join(segment.capitalize() for segment in value.split("_") if segment)


def _parse_utc_datetime(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


if __name__ == "__main__":
    main()
