import { useEffect, useState } from "react";

import {
  fetchAuthorOverview,
  fetchBtcSpotPrice,
  fetchAuthorSentiment,
  type AuthorOverviewResponse,
  type BtcSpotPriceResponse,
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
  showWatermark: boolean;
};

export function AuthorOverviewPage({
  overview,
  showWatermark,
}: AuthorOverviewPageProps) {
  const [payload, setPayload] = useState<AuthorOverviewResponse | null>(null);
  const [sentimentPayload, setSentimentPayload] = useState<AuthorSentimentResponse | null>(
    null,
  );
  const [btcSpotPayload, setBtcSpotPayload] = useState<BtcSpotPriceResponse | null>(null);
  const [isScreenshotMode, setIsScreenshotMode] = useState(false);
  const [sentimentMode, setSentimentMode] = useState<SentimentMode>("weighted-8w");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const overviewLabel = getOverviewLabel(overview);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const [requiredResponses, btcSpotResult] = await Promise.all([
          Promise.all([
            fetchAuthorOverview(overview.apiBasePath, "week"),
            fetchAuthorSentiment(overview.apiBasePath, "week"),
          ]),
          fetchBtcSpotPrice(overview.apiBasePath)
            .then((response) => ({ ok: true as const, response }))
            .catch((spotError: unknown) => ({ ok: false as const, spotError })),
        ]);
        const [response, sentimentResponse] = requiredResponses;

        if (!cancelled) {
          setPayload(response);
          setSentimentPayload(sentimentResponse);
          setBtcSpotPayload(btcSpotResult.ok ? btcSpotResult.response : null);
          setError(null);
        }

        console.log("ChartProject overview sentiment payload", overview.slug, sentimentResponse);
        if (!btcSpotResult.ok) {
          console.warn("ChartProject BTC spot request failed", overview.slug, btcSpotResult.spotError);
        }
      } catch (loadError) {
        console.error("ChartProject overview request failed", overview.slug, loadError);
        if (!cancelled) {
          setPayload(null);
          setSentimentPayload(null);
          setBtcSpotPayload(null);
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
            btcSpotPayload={btcSpotPayload}
            showWatermark={showWatermark}
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

function AuthorOverviewChartSection({
  overview,
  payload,
  sentimentPayload,
  btcSpotPayload,
  showWatermark,
  isScreenshotMode,
  onScreenshotModeChange,
  sentimentMode,
  onSentimentModeChange,
}: {
  overview: OverviewDefinition;
  payload: AuthorOverviewResponse;
  sentimentPayload: AuthorSentimentResponse;
  btcSpotPayload: BtcSpotPriceResponse | null;
  showWatermark: boolean;
  isScreenshotMode: boolean;
  onScreenshotModeChange: (enabled: boolean) => void;
  sentimentMode: SentimentMode;
  onSentimentModeChange: (mode: SentimentMode) => void;
}) {
  const postCounts = payload.tweet_series.map((point) => point.tweet_count);
  const totalPosts = postCounts.reduce((sum, value) => sum + value, 0);
  const maxPostWeek = postCounts.reduce((max, value) => Math.max(max, value), 0);
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  const latestBtcDailyClose = latestBtcPoint?.price_usd ?? 0;
  const btcLastIso = latestBtcPoint?.timestamp ?? payload.range.end;
  const latestBtc = btcSpotPayload?.price_usd ?? latestBtcDailyClose;
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
      <div
        className={`metric-strip metric-strip-dashboard${isScreenshotMode ? " is-screenshot-mode" : ""}`}
      >
        <article className="metric-card">
          <p className="metric-label">Analyzed posts</p>
          <p className="metric-value">{integerFormatter.format(totalPosts)}</p>
          <p className="metric-note">Across {payload.tweet_series.length} weekly buckets</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Peak week</p>
          <p className="metric-value">{integerFormatter.format(maxPostWeek)}</p>
          <p className="metric-note">Posts in the busiest week</p>
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
          <p className="metric-label">Latest MSTR Price</p>
          <p className="metric-value">{chartCurrencyFormatter.format(latestMstr)}</p>
          <p className="metric-note">Price on {formatFullDate(mstrLastIso)}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Current Sentiment Deviation</p>
          <p className="metric-value">{formatSignedPercent(currentSentimentDeviation.value)}</p>
          <p className="metric-note">
            {describeSentimentMode(sentimentMode, currentSentimentDeviation.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Best Sentiment</p>
          <p className="metric-value">{formatSignedPercent(sentimentExtremes.best.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(sentimentExtremes.best.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Worst Sentiment</p>
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
          showWatermark={showWatermark}
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
