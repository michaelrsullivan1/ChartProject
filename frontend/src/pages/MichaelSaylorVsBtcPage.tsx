import { useEffect, useState } from "react";

import {
  fetchAuthorOverview,
  fetchAuthorSentiment,
  type AuthorOverviewResponse,
  type AuthorSentimentResponse,
} from "../api/authorOverview";
import { type OverviewDefinition, getOverviewLabel } from "../config/overviews";
import { MichaelSaylorVsBtcTradingViewChart } from "../components/MichaelSaylorVsBtcTradingViewChart";
import {
  buildSentimentDeviationSeries,
  type SentimentMode,
} from "../lib/sentiment";

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

type AuthorOverviewPageProps = {
  overview: OverviewDefinition;
};

export function AuthorOverviewPage({ overview }: AuthorOverviewPageProps) {
  const [payload, setPayload] = useState<AuthorOverviewResponse | null>(null);
  const [sentimentPayload, setSentimentPayload] = useState<AuthorSentimentResponse | null>(
    null,
  );
  const [sentimentMode, setSentimentMode] = useState<SentimentMode>("weighted-8w");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const overviewLabel = getOverviewLabel(overview);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const [response, sentimentResponse] = await Promise.all([
          fetchAuthorOverview(overview.apiBasePath, "week"),
          fetchAuthorSentiment(overview.apiBasePath, "week"),
        ]);

        if (!cancelled) {
          setPayload(response);
          setSentimentPayload(sentimentResponse);
          setError(null);
        }

        console.log("ChartProject overview sentiment payload", overview.slug, sentimentResponse);
      } catch (loadError) {
        console.error("ChartProject overview request failed", overview.slug, loadError);
        if (!cancelled) {
          setPayload(null);
          setSentimentPayload(null);
          setError(
            loadError instanceof Error ? loadError.message : "Unknown overview fetch failure",
          );
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
  }, [overview]);

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          {isLoading ? <p className="status-copy">Loading {overviewLabel} view...</p> : null}
          {error ? <p className="status-copy">{error}</p> : null}
        </div>
        {payload && sentimentPayload ? (
          <AuthorOverviewChartSection
            overview={overview}
            payload={payload}
            sentimentPayload={sentimentPayload}
            sentimentMode={sentimentMode}
            onSentimentModeChange={setSentimentMode}
          />
        ) : null}
      </article>
    </section>
  );
}

function AuthorOverviewChartSection({
  overview,
  payload,
  sentimentPayload,
  sentimentMode,
  onSentimentModeChange,
}: {
  overview: OverviewDefinition;
  payload: AuthorOverviewResponse;
  sentimentPayload: AuthorSentimentResponse;
  sentimentMode: SentimentMode;
  onSentimentModeChange: (mode: SentimentMode) => void;
}) {
  const tweetCounts = payload.tweet_series.map((point) => point.tweet_count);
  const totalTweets = tweetCounts.reduce((sum, value) => sum + value, 0);
  const maxTweetWeek = tweetCounts.reduce((max, value) => Math.max(max, value), 0);
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  const latestBtc = latestBtcPoint?.price_usd ?? 0;
  const btcLastIso = latestBtcPoint?.timestamp ?? payload.range.end;
  const latestMstrPoint = payload.mstr_series[payload.mstr_series.length - 1];
  const latestMstr = latestMstrPoint?.price_usd ?? 0;
  const mstrLastIso = latestMstrPoint?.timestamp ?? payload.range.end;
  const sentimentDeviationSeries = buildSentimentDeviationSeries(sentimentPayload, sentimentMode);
  const currentSentimentDeviation = getCurrentSentimentDeviation(
    sentimentDeviationSeries,
    sentimentPayload.range.end,
  );
  const sentimentExtremes = getSentimentExtremes(
    sentimentDeviationSeries,
    sentimentPayload.range.end,
  );

  return (
    <>
      <div className="metric-strip metric-strip-dashboard">
        <article className="metric-card">
          <p className="metric-label">Authored tweets</p>
          <p className="metric-value">{integerFormatter.format(totalTweets)}</p>
          <p className="metric-note">Across {payload.tweet_series.length} weekly buckets</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Peak week</p>
          <p className="metric-value">{integerFormatter.format(maxTweetWeek)}</p>
          <p className="metric-note">Tweets in the busiest week</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Latest BTC</p>
          <p className="metric-value">{chartCurrencyFormatter.format(latestBtc)}</p>
          <p className="metric-note">Daily close from {formatFullDate(btcLastIso)}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Latest MSTR</p>
          <p className="metric-value">{chartCurrencyFormatter.format(latestMstr)}</p>
          <p className="metric-note">Daily close from {formatFullDate(mstrLastIso)}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Current Sentiment Deviation</p>
          <p className="metric-value">{formatSignedPercent(currentSentimentDeviation.value)}</p>
          <p className="metric-note">
            Most recent scored week from {formatCompactDate(currentSentimentDeviation.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Best Sentiment Week</p>
          <p className="metric-value">{formatSignedPercent(sentimentExtremes.best.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(sentimentExtremes.best.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Worst Sentiment Week</p>
          <p className="metric-value">{formatSignedPercent(sentimentExtremes.worst.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(sentimentExtremes.worst.periodStart)}
          </p>
        </article>
      </div>

      <div className="chart-shell chart-shell-dashboard">
        <MichaelSaylorVsBtcTradingViewChart
          overview={overview}
          payload={payload}
          sentimentPayload={sentimentPayload}
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
            <span className="chart-swatch chart-swatch-mstr" />
            MSTR line
          </span>
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-tweet" />
            Weekly activity pane
          </span>
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-sentiment" />
            Sentiment deviation
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

function formatSignedPercent(value: number): string {
  const percentage = value * 100;
  const formatted = percentage.toFixed(1);
  return percentage > 0 ? `+${formatted}%` : `${formatted}%`;
}

function getCurrentSentimentDeviation(
  sentimentSeries: ReturnType<typeof buildSentimentDeviationSeries>,
  fallbackPeriodStart: string,
): {
  periodStart: string;
  value: number;
} {
  const latestScoredPoint =
    [...sentimentSeries]
      .reverse()
      .find((point) => point.value !== null) ?? null;

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

function getSentimentExtremes(
  sentimentSeries: ReturnType<typeof buildSentimentDeviationSeries>,
  fallbackPeriodStart: string,
): {
  best: { periodStart: string; value: number };
  worst: { periodStart: string; value: number };
} {
  const scoredPoints = sentimentSeries.filter(
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

function normalizeDateValue(value: string | number): Date | number {
  return typeof value === "string" ? new Date(value) : value;
}
