import { useEffect, useState } from "react";

import {
  fetchAuthorMoods,
  fetchAuthorOverview,
  fetchBtcSpotPrice,
  type AuthorMoodResponse,
  type AuthorOverviewResponse,
  type BtcSpotPriceResponse,
} from "../api/authorOverview";
import { AuthorMoodTradingViewChart } from "../components/AuthorMoodTradingViewChart";
import { DashboardLoadingState } from "../components/DashboardLoadingState";
import {
  type AggregateMoodDefinition,
  getAggregateMoodLabel,
} from "../config/aggregateMoods";
import { buildMoodDeviationSeries } from "../lib/moods";
import { type SentimentMode } from "../lib/sentiment";

const chartCurrencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const integerFormatter = new Intl.NumberFormat("en-US");

const fullDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const compactDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

type AggregateMoodPageProps = {
  aggregateMood: AggregateMoodDefinition;
  showWatermark: boolean;
};

export function AggregateMoodPage({ aggregateMood, showWatermark }: AggregateMoodPageProps) {
  const [payload, setPayload] = useState<AuthorOverviewResponse | null>(null);
  const [moodPayload, setMoodPayload] = useState<AuthorMoodResponse | null>(null);
  const [btcSpotPayload, setBtcSpotPayload] = useState<BtcSpotPriceResponse | null>(null);
  const [sentimentMode, setSentimentMode] = useState<SentimentMode>("weighted-8w");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const moodLabel = getAggregateMoodLabel(aggregateMood);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const [requiredResponses, btcSpotResult] = await Promise.all([
          Promise.all([
            fetchAuthorOverview(aggregateMood.apiBasePath, "week"),
            fetchAuthorMoods(aggregateMood.apiBasePath, "week"),
          ]),
          fetchBtcSpotPrice(aggregateMood.apiBasePath)
            .then((response) => ({ ok: true as const, response }))
            .catch((spotError: unknown) => ({ ok: false as const, spotError })),
        ]);
        const [response, moodResponse] = requiredResponses;

        if (!cancelled) {
          setPayload(response);
          setMoodPayload(moodResponse);
          setBtcSpotPayload(btcSpotResult.ok ? btcSpotResult.response : null);
          setError(null);
        }

        if (!btcSpotResult.ok) {
          console.warn(
            "ChartProject aggregate BTC spot request failed",
            aggregateMood.slug,
            btcSpotResult.spotError,
          );
        }
      } catch (loadError) {
        console.error("ChartProject aggregate mood request failed", aggregateMood.slug, loadError);
        if (!cancelled) {
          setPayload(null);
          setMoodPayload(null);
          setBtcSpotPayload(null);
          setError(loadError instanceof Error ? loadError.message : "Unknown mood fetch failure");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    setError(null);
    setPayload(null);
    setMoodPayload(null);
    setBtcSpotPayload(null);
    void loadView();

    return () => {
      cancelled = true;
    };
  }, [aggregateMood]);

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        {isLoading ? <DashboardLoadingState /> : null}
        {!isLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null}
        {!isLoading && payload && moodPayload ? (
          <AggregateMoodChartSection
            payload={payload}
            moodPayload={moodPayload}
            btcSpotPayload={btcSpotPayload}
            showWatermark={showWatermark}
            selectedMoodLabel={aggregateMood.moodLabel}
            sentimentMode={sentimentMode}
            onSentimentModeChange={setSentimentMode}
          />
        ) : null}
      </article>
    </section>
  );
}

function AggregateMoodChartSection({
  payload,
  moodPayload,
  btcSpotPayload,
  showWatermark,
  selectedMoodLabel,
  sentimentMode,
  onSentimentModeChange,
}: {
  payload: AuthorOverviewResponse;
  moodPayload: AuthorMoodResponse;
  btcSpotPayload: BtcSpotPriceResponse | null;
  showWatermark: boolean;
  selectedMoodLabel: string;
  sentimentMode: SentimentMode;
  onSentimentModeChange: (mode: SentimentMode) => void;
}) {
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  const latestBtcDailyClose = latestBtcPoint?.price_usd ?? 0;
  const btcLastIso = latestBtcPoint?.timestamp ?? payload.range.end;
  const latestBtc = btcSpotPayload?.price_usd ?? latestBtcDailyClose;
  const moodDeviationSeries = buildMoodDeviationSeries(
    moodPayload,
    selectedMoodLabel,
    sentimentMode,
  );
  const currentMoodDeviation = getCurrentMoodDeviation(moodDeviationSeries, moodPayload.range.end);
  const moodExtremes = getMoodExtremes(moodDeviationSeries, moodPayload.range.end);
  const selectedMoodSummary = moodPayload.summary.moods[selectedMoodLabel];
  const cohortUserCount =
    moodPayload.summary.cohort_user_count ?? moodPayload.cohort?.user_count ?? 0;

  return (
    <>
      <div className="metric-strip metric-strip-dashboard">
        <article className="metric-card">
          <p className="metric-label">Tracked users</p>
          <p className="metric-value">{integerFormatter.format(cohortUserCount)}</p>
          <p className="metric-note">Accounts with stored mood scores</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Analyzed posts</p>
          <p className="metric-value">
            {integerFormatter.format(moodPayload.summary.scored_tweet_count)}
          </p>
          <p className="metric-note">Scored posts across the tracked cohort</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Tracked mood</p>
          <p className="metric-value">{formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-note">Selected from the Aggregate Moods navigation</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Baseline mood score</p>
          <p className="metric-value">{formatPercent(selectedMoodSummary?.average_score ?? 0)}</p>
          <p className="metric-note">Average personal baseline across tracked users</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Latest BTC Price</p>
          <p className="metric-value">{chartCurrencyFormatter.format(latestBtc)}</p>
          <p className="metric-note">
            {btcSpotPayload
              ? `Coinbase spot on ${formatFullDate(btcSpotPayload.fetched_at)}`
              : `Price on ${formatFullDate(btcLastIso)}`}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Current Mood Deviation</p>
          <p className="metric-value">{formatSignedPercent(currentMoodDeviation.value)}</p>
          <p className="metric-note">
            {describeSentimentMode(sentimentMode, currentMoodDeviation.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Highest Aggregate {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.best.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(moodExtremes.best.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Lowest Aggregate {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.worst.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(moodExtremes.worst.periodStart)}
          </p>
        </article>
      </div>

      <div className="chart-shell chart-shell-dashboard">
        <AuthorMoodTradingViewChart
          payload={payload}
          moodPayload={moodPayload}
          showWatermark={showWatermark}
          showMoodSelector={false}
          selectedMoodLabel={selectedMoodLabel}
          onMoodLabelChange={() => {}}
          sentimentMode={sentimentMode}
          smoothingWeightLabel="active user count"
          onSentimentModeChange={onSentimentModeChange}
        />
      </div>

      <div className="chart-caption-row chart-caption-row-dashboard">
        <div className="chart-legend" aria-label="Chart legend">
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-btc" />
            BTC/USD line
          </span>
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-sentiment" />
            Aggregate {formatMoodLabel(selectedMoodLabel)} deviation
          </span>
        </div>
      </div>
    </>
  );
}

function formatFullDate(value: string | number): string {
  return fullDateFormatter.format(normalizeDateValue(value));
}

function formatCompactDate(value: string): string {
  return compactDateFormatter.format(new Date(value));
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatSignedPercent(value: number): string {
  const percentage = value * 100;
  const formatted = percentage.toFixed(1);
  return percentage > 0 ? `+${formatted}%` : `${formatted}%`;
}

function describeSentimentMode(mode: SentimentMode, _periodStart: string): string {
  switch (mode) {
    case "weighted-4w":
      return "Smoothed using a 4-week WMA.";
    case "weighted-8w":
      return "Smoothed using an 8-week WMA.";
    case "weighted-12w":
      return "Smoothed using a 12-week WMA.";
    case "raw":
      return "Using the raw weekly score.";
  }
}

function getCurrentMoodDeviation(
  moodSeries: ReturnType<typeof buildMoodDeviationSeries>,
  fallbackPeriodStart: string,
): {
  periodStart: string;
  value: number;
} {
  const latestScoredPoint =
    [...moodSeries].reverse().find((point) => point.value !== null) ?? null;

  if (!latestScoredPoint) {
    return {
      periodStart: fallbackPeriodStart,
      value: 0,
    };
  }

  return {
    periodStart: latestScoredPoint.periodStart,
    value: latestScoredPoint.value ?? 0,
  };
}

function getMoodExtremes(
  moodSeries: ReturnType<typeof buildMoodDeviationSeries>,
  fallbackPeriodStart: string,
): {
  best: { periodStart: string; value: number };
  worst: { periodStart: string; value: number };
} {
  const scoredPoints = moodSeries.filter(
    (point): point is { periodStart: string; value: number } => point.value !== null,
  );

  if (scoredPoints.length === 0) {
    const fallback = {
      periodStart: fallbackPeriodStart,
      value: 0,
    };

    return {
      best: fallback,
      worst: fallback,
    };
  }

  let bestPoint = scoredPoints[0];
  let worstPoint = scoredPoints[0];

  for (const point of scoredPoints) {
    if (point.value > bestPoint.value) {
      bestPoint = point;
    }

    if (point.value < worstPoint.value) {
      worstPoint = point;
    }
  }

  return {
    best: {
      periodStart: bestPoint.periodStart,
      value: bestPoint.value,
    },
    worst: {
      periodStart: worstPoint.periodStart,
      value: worstPoint.value,
    },
  };
}

function formatMoodLabel(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function normalizeDateValue(value: string | number): Date | number {
  return typeof value === "string" ? new Date(value) : value;
}
