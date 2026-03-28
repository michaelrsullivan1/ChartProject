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

const analysisStartIso = "2020-08-01T00:00:00Z";
const analysisStartTimestamp = new Date(analysisStartIso).getTime();

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
  const filteredPayload = filterAuthorViewPayload(payload);
  const filteredSentimentPayload = filterSentimentViewPayload(sentimentPayload);
  const tweetCounts = filteredPayload.tweet_series.map((point) => point.tweet_count);
  const totalTweets = tweetCounts.reduce((sum, value) => sum + value, 0);
  const maxTweetWeek = tweetCounts.reduce((max, value) => Math.max(max, value), 0);
  const latestBtcPoint = filteredPayload.btc_series[filteredPayload.btc_series.length - 1];
  const latestBtc = latestBtcPoint?.price_usd ?? 0;
  const btcLastIso = latestBtcPoint?.timestamp ?? filteredPayload.range.end;
  const latestMstrPoint = filteredPayload.mstr_series[filteredPayload.mstr_series.length - 1];
  const latestMstr = latestMstrPoint?.price_usd ?? 0;
  const mstrLastIso = latestMstrPoint?.timestamp ?? filteredPayload.range.end;
  const currentSentimentDeviation = getCurrentSentimentDeviation(filteredSentimentPayload);
  const sentimentExtremes = getSentimentExtremes(filteredSentimentPayload);

  return (
    <>
      <div className="metric-strip metric-strip-dashboard">
        <article className="metric-card">
          <p className="metric-label">Authored tweets</p>
          <p className="metric-value">{integerFormatter.format(totalTweets)}</p>
          <p className="metric-note">Across {filteredPayload.tweet_series.length} weekly buckets</p>
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
          payload={filteredPayload}
          sentimentPayload={filteredSentimentPayload}
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

function filterAuthorViewPayload(payload: MichaelSaylorVsBtcResponse): MichaelSaylorVsBtcResponse {
  const tweetSeries = payload.tweet_series.filter((point) => toTimestamp(point.period_start) >= analysisStartTimestamp);
  const btcSeries = payload.btc_series.filter((point) => toTimestamp(point.timestamp) >= analysisStartTimestamp);
  const mstrSeries = payload.mstr_series.filter((point) => toTimestamp(point.timestamp) >= analysisStartTimestamp);

  return {
    ...payload,
    range: {
      start: analysisStartIso,
      end: payload.range.end,
    },
    tweet_series: tweetSeries,
    btc_series: btcSeries,
    mstr_series: mstrSeries,
  };
}

function filterSentimentViewPayload(
  sentimentPayload: MichaelSaylorSentimentResponse,
): MichaelSaylorSentimentResponse {
  const sentimentSeries = sentimentPayload.sentiment_series.filter(
    (point) => toTimestamp(point.period_start) >= analysisStartTimestamp,
  );
  const filteredSummary = buildFilteredSentimentSummary(sentimentSeries);

  return {
    ...sentimentPayload,
    range: {
      start: analysisStartIso,
      end: sentimentPayload.range.end,
    },
    summary: filteredSummary,
    sentiment_series: sentimentSeries,
  };
}

function buildFilteredSentimentSummary(
  sentimentSeries: MichaelSaylorSentimentResponse["sentiment_series"],
): MichaelSaylorSentimentResponse["summary"] {
  let scoredTweetCount = 0;
  let weightedSentimentSum = 0;
  let weightedConfidenceSum = 0;
  let negativeTweetCount = 0;
  let neutralTweetCount = 0;
  let positiveTweetCount = 0;

  for (const point of sentimentSeries) {
    scoredTweetCount += point.scored_tweet_count;
    weightedSentimentSum += point.average_sentiment_index * point.scored_tweet_count;
    weightedConfidenceSum += point.average_confidence * point.scored_tweet_count;
    negativeTweetCount += point.negative_tweet_count;
    neutralTweetCount += point.neutral_tweet_count;
    positiveTweetCount += point.positive_tweet_count;
  }

  if (scoredTweetCount === 0) {
    return {
      scored_tweet_count: 0,
      average_sentiment_index: 0,
      average_confidence: 0,
      negative_tweet_count: 0,
      neutral_tweet_count: 0,
      positive_tweet_count: 0,
    };
  }

  return {
    scored_tweet_count: scoredTweetCount,
    average_sentiment_index: weightedSentimentSum / scoredTweetCount,
    average_confidence: weightedConfidenceSum / scoredTweetCount,
    negative_tweet_count: negativeTweetCount,
    neutral_tweet_count: neutralTweetCount,
    positive_tweet_count: positiveTweetCount,
  };
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

function toTimestamp(value: string): number {
  return new Date(value).getTime();
}
