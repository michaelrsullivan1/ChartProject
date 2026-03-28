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

const monthYearFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
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
          <div>
            <p className="eyebrow dashboard-eyebrow">Michael Saylor vs BTC</p>
            <p className="dashboard-subtitle">
              Synced price, activity, and sentiment panes with a shared research timeline.
            </p>
          </div>
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
  const zeroTweetWeeks = tweetCounts.filter((value) => value === 0).length;
  const maxTweetWeek = tweetCounts.reduce((max, value) => Math.max(max, value), 0);
  const averageSentimentIndex = sentimentPayload.summary.average_sentiment_index;
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  const latestBtc = latestBtcPoint?.price_usd ?? 0;
  const btcFirstIso = payload.btc_series[0]?.timestamp ?? payload.range.start;
  const btcLastIso = latestBtcPoint?.timestamp ?? payload.range.end;
  const zeroWeekShare =
    tweetCounts.length === 0 ? 0 : (zeroTweetWeeks / payload.tweet_series.length) * 100;

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
          <p className="metric-label">Zero-filled weeks</p>
          <p className="metric-value">{Math.round(zeroWeekShare)}%</p>
          <p className="metric-note">{integerFormatter.format(zeroTweetWeeks)} weeks at zero</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Baseline Sentiment</p>
          <p className="metric-value">{formatSignedDecimal(averageSentimentIndex, 3)}</p>
          <p className="metric-note">Average sentiment index across scored tweets</p>
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
            Sentiment deviation from baseline
          </span>
        </div>
        <p className="chart-caption">
          Shared x-axis from {formatMonthYear(payload.range.start)} to {formatMonthYear(btcLastIso)}.
          BTC coverage begins in {formatMonthYear(btcFirstIso)}, so the early tweet-only stretch is
          preserved rather than cropped away. The sentiment pane is centered at zero and tracks
          weekly deviation from Saylor&apos;s overall average sentiment score.
        </p>
      </div>
    </>
  );
}

function formatMonthYear(value: string | number): string {
  return monthYearFormatter.format(normalizeDateValue(value));
}

function formatFullDate(value: string | number): string {
  return fullDateFormatter.format(normalizeDateValue(value));
}

function formatSignedDecimal(value: number, fractionDigits: number): string {
  const formatted = value.toFixed(fractionDigits);
  return value > 0 ? `+${formatted}` : formatted;
}

function normalizeDateValue(value: string | number): Date | number {
  return typeof value === "string" ? new Date(value) : value;
}
