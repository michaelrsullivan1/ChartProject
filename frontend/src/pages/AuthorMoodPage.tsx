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
import { type MoodDefinition, getMoodLabel } from "../config/moods";
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

type AuthorMoodPageProps = {
  mood: MoodDefinition;
};

export function AuthorMoodPage({ mood }: AuthorMoodPageProps) {
  const [payload, setPayload] = useState<AuthorOverviewResponse | null>(null);
  const [moodPayload, setMoodPayload] = useState<AuthorMoodResponse | null>(null);
  const [btcSpotPayload, setBtcSpotPayload] = useState<BtcSpotPriceResponse | null>(null);
  const [selectedMoodLabel, setSelectedMoodLabel] = useState<string>("optimism");
  const [isScreenshotMode, setIsScreenshotMode] = useState(false);
  const [sentimentMode, setSentimentMode] = useState<SentimentMode>("weighted-8w");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const moodLabel = getMoodLabel(mood);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const [requiredResponses, btcSpotResult] = await Promise.all([
          Promise.all([
            fetchAuthorOverview(mood.apiBasePath, "week"),
            fetchAuthorMoods(mood.apiBasePath, "week"),
          ]),
          fetchBtcSpotPrice(mood.apiBasePath)
            .then((response) => ({ ok: true as const, response }))
            .catch((spotError: unknown) => ({ ok: false as const, spotError })),
        ]);
        const [response, moodResponse] = requiredResponses;

        if (!cancelled) {
          setPayload(response);
          setMoodPayload(moodResponse);
          setBtcSpotPayload(btcSpotResult.ok ? btcSpotResult.response : null);
          setSelectedMoodLabel((current) =>
            moodResponse.model.mood_labels.includes(current)
              ? current
              : (moodResponse.model.mood_labels[0] ?? "optimism"),
          );
          setError(null);
        }

        if (!btcSpotResult.ok) {
          console.warn("ChartProject BTC spot request failed", mood.slug, btcSpotResult.spotError);
        }
      } catch (loadError) {
        console.error("ChartProject mood request failed", mood.slug, loadError);
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
    void loadView();

    return () => {
      cancelled = true;
    };
  }, [mood]);

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          {isLoading ? <p className="status-copy">Loading {moodLabel} moods...</p> : null}
          {error ? <p className="status-copy">{error}</p> : null}
        </div>
        {payload && moodPayload ? (
          <AuthorMoodChartSection
            payload={payload}
            moodPayload={moodPayload}
            btcSpotPayload={btcSpotPayload}
            selectedMoodLabel={selectedMoodLabel}
            onMoodLabelChange={setSelectedMoodLabel}
            isScreenshotMode={isScreenshotMode}
            onScreenshotModeChange={setIsScreenshotMode}
            sentimentMode={sentimentMode}
            onSentimentModeChange={setSentimentMode}
          />
        ) : null}
      </article>
    </section>
  );
}

function AuthorMoodChartSection({
  payload,
  moodPayload,
  btcSpotPayload,
  selectedMoodLabel,
  onMoodLabelChange,
  isScreenshotMode,
  onScreenshotModeChange,
  sentimentMode,
  onSentimentModeChange,
}: {
  payload: AuthorOverviewResponse;
  moodPayload: AuthorMoodResponse;
  btcSpotPayload: BtcSpotPriceResponse | null;
  selectedMoodLabel: string;
  onMoodLabelChange: (label: string) => void;
  isScreenshotMode: boolean;
  onScreenshotModeChange: (enabled: boolean) => void;
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

  return (
    <>
      <div
        className={`metric-strip metric-strip-dashboard${isScreenshotMode ? " is-screenshot-mode" : ""}`}
      >
        <article className="metric-card">
          <p className="metric-label">Analyzed posts</p>
          <p className="metric-value">
            {integerFormatter.format(moodPayload.summary.scored_tweet_count)}
          </p>
          <p className="metric-note">Posts with stored mood scores</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Tracked mood</p>
          <p className="metric-value">{formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-note">Selected from the stored model labels</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Baseline mood score</p>
          <p className="metric-value">{formatPercent(selectedMoodSummary?.average_score ?? 0)}</p>
          <p className="metric-note">Per-account average absolute score</p>
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
          <p className="metric-label">Highest {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.best.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(moodExtremes.best.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Lowest {formatMoodLabel(selectedMoodLabel)}</p>
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
          selectedMoodLabel={selectedMoodLabel}
          onMoodLabelChange={onMoodLabelChange}
          isScreenshotMode={isScreenshotMode}
          onScreenshotModeChange={onScreenshotModeChange}
          sentimentMode={sentimentMode}
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
            {formatMoodLabel(selectedMoodLabel)} deviation
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
