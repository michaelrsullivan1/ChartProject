import { useEffect, useState } from "react";

import {
  fetchMichaelSaylorVsBtc,
  type MichaelSaylorVsBtcResponse,
} from "../api/michaelSaylorVsBtc";
import {
  fetchMichaelSaylorSentiment,
  type MichaelSaylorSentimentResponse,
} from "../api/michaelSaylorSentiment";
import { MichaelSaylorVsBtcTradingViewChart } from "../components/MichaelSaylorVsBtcTradingViewChart";

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

export function MichaelSaylorVsBtcPage() {
  const [payload, setPayload] = useState<MichaelSaylorVsBtcResponse | null>(null);
  const [sentimentPayload, setSentimentPayload] = useState<MichaelSaylorSentimentResponse | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const [response, sentimentResponse] = await Promise.all([
          fetchMichaelSaylorVsBtc("week"),
          fetchMichaelSaylorSentiment("week"),
        ]);
        if (!cancelled) {
          setPayload(response);
          setSentimentPayload(sentimentResponse);
          setError(null);
        }
        console.log("ChartProject michael-saylor sentiment payload", sentimentResponse);
      } catch (loadError) {
        console.error("ChartProject michael-saylor-vs-btc request failed", loadError);
        if (!cancelled) {
          setPayload(null);
          setSentimentPayload(null);
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unknown michael-saylor-vs-btc fetch failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadView();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          {isLoading ? <p className="status-copy">Loading Michael Saylor view...</p> : null}
          {error ? <p className="status-copy">{error}</p> : null}
        </div>
        {payload && sentimentPayload ? (
          <MichaelSaylorChartSection
            payload={payload}
            sentimentPayload={sentimentPayload}
          />
        ) : null}
      </article>
    </section>
  );
}

function MichaelSaylorChartSection({
  payload,
  sentimentPayload,
}: {
  payload: MichaelSaylorVsBtcResponse;
  sentimentPayload: MichaelSaylorSentimentResponse;
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
  const currentSentimentDeviation = getCurrentSentimentDeviation(sentimentPayload);
  const sentimentExtremes = getSentimentExtremes(sentimentPayload);

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
          <p className="metric-label">Best / Worst Sentiment Weeks</p>
          <p className="metric-value">
            {formatSignedPercent(sentimentExtremes.best.value)} /{" "}
            {formatSignedPercent(sentimentExtremes.worst.value)}
          </p>
          <p className="metric-note">
            Best {formatCompactDate(sentimentExtremes.best.periodStart)} · Worst{" "}
            {formatCompactDate(sentimentExtremes.worst.periodStart)}
          </p>
        </article>
      </div>

      <div className="chart-shell chart-shell-dashboard">
        <MichaelSaylorVsBtcTradingViewChart
          payload={payload}
          sentimentPayload={sentimentPayload}
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

function getCurrentSentimentDeviation(sentimentPayload: MichaelSaylorSentimentResponse): {
  periodStart: string;
  value: number;
} {
  const baseline = sentimentPayload.summary.average_sentiment_index;
  const latestPoint =
    sentimentPayload.sentiment_series[sentimentPayload.sentiment_series.length - 1] ?? null;
  const latestScoredPoint =
    [...sentimentPayload.sentiment_series]
      .reverse()
      .find((point) => point.scored_tweet_count > 0) ?? latestPoint;

  if (!latestScoredPoint) {
    return {
      periodStart: sentimentPayload.range.end,
      value: 0,
    };
  }

  return {
    periodStart: latestScoredPoint.period_start,
    value: latestScoredPoint.average_sentiment_index - baseline,
  };
}

function getSentimentExtremes(sentimentPayload: MichaelSaylorSentimentResponse): {
  best: { periodStart: string; value: number };
  worst: { periodStart: string; value: number };
} {
  const baseline = sentimentPayload.summary.average_sentiment_index;
  const scoredPoints = sentimentPayload.sentiment_series.filter((point) => point.scored_tweet_count > 0);

  if (scoredPoints.length === 0) {
    const fallback = {
      periodStart: sentimentPayload.range.end,
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
    if (point.average_sentiment_index > bestPoint.average_sentiment_index) {
      bestPoint = point;
    }

    if (point.average_sentiment_index < worstPoint.average_sentiment_index) {
      worstPoint = point;
    }
  }

  return {
    best: {
      periodStart: bestPoint.period_start,
      value: bestPoint.average_sentiment_index - baseline,
    },
    worst: {
      periodStart: worstPoint.period_start,
      value: worstPoint.average_sentiment_index - baseline,
    },
  };
}

function normalizeDateValue(value: string | number): Date | number {
  return typeof value === "string" ? new Date(value) : value;
}
