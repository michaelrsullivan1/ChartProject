import { useEffect, useState } from "react";

import {
  fetchMichaelSaylorVsBtc,
  type MichaelSaylorVsBtcResponse,
} from "../api/michaelSaylorVsBtc";
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
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const response = await fetchMichaelSaylorVsBtc("week");
        if (!cancelled) {
          setPayload(response);
          setError(null);
        }
      } catch (loadError) {
        console.error("ChartProject michael-saylor-vs-btc request failed", loadError);
        if (!cancelled) {
          setPayload(null);
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
    <section className="content-stack">
      <article className="panel panel-accent">
        <h2>Michael Saylor vs BTC</h2>
        <p className="status-copy">
          TradingView Lightweight Charts now renders the dedicated Michael Saylor view with synced
          panes, pan and zoom, and a shared timeline across BTC and tweet activity.
        </p>
        {isLoading ? <p className="status-copy">Loading Michael Saylor view...</p> : null}
        {error ? <p className="status-copy">{error}</p> : null}
        {payload ? <MichaelSaylorChartSection payload={payload} /> : null}
      </article>

      {payload ? (
        <div className="content-grid">
          <article className="panel">
            <h2>Rendered from</h2>
            <dl className="status-grid">
              <div>
                <dt>Endpoint</dt>
                <dd>
                  <code>/api/views/michael-saylor-vs-btc?granularity=week</code>
                </dd>
              </div>
              <div>
                <dt>Tweet Series</dt>
                <dd>
                  {payload.tweet_series.length} weekly points, zero-filled, replies and quote
                  tweets included
                </dd>
              </div>
              <div>
                <dt>BTC Series</dt>
                <dd>{payload.btc_series.length} daily points from local FRED archive</dd>
              </div>
              <div>
                <dt>Timeline</dt>
                <dd>
                  {formatMonthYear(payload.range.start)} to{" "}
                  {formatMonthYear(
                    payload.btc_series[payload.btc_series.length - 1]?.timestamp ?? payload.range.end,
                  )}
                </dd>
              </div>
            </dl>
          </article>

          <article className="panel">
            <h2>Immediate read</h2>
            <ul className="feature-list">
              <li>
                The tweet history begins in {formatMonthYear(payload.range.start)}, while BTC data
                only starts in {formatMonthYear(payload.btc_series[0]?.timestamp ?? payload.range.start)}.
              </li>
              <li>
                Weekly tweet activity is sparse for long stretches because the series is explicitly
                zero-filled.
              </li>
              <li>
                Daily BTC next to weekly tweet buckets is readable in separate panes, but the
                cadence mismatch is now much easier to inspect.
              </li>
            </ul>
          </article>
        </div>
      ) : null}
    </section>
  );
}

function MichaelSaylorChartSection({ payload }: { payload: MichaelSaylorVsBtcResponse }) {
  const tweetCounts = payload.tweet_series.map((point) => point.tweet_count);
  const totalTweets = tweetCounts.reduce((sum, value) => sum + value, 0);
  const zeroTweetWeeks = tweetCounts.filter((value) => value === 0).length;
  const maxTweetWeek = tweetCounts.reduce((max, value) => Math.max(max, value), 0);
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  const latestBtc = latestBtcPoint?.price_usd ?? 0;
  const btcFirstIso = payload.btc_series[0]?.timestamp ?? payload.range.start;
  const btcLastIso = latestBtcPoint?.timestamp ?? payload.range.end;
  const zeroWeekShare =
    tweetCounts.length === 0 ? 0 : (zeroTweetWeeks / payload.tweet_series.length) * 100;

  return (
    <>
      <div className="metric-strip">
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
      </div>

      <div className="chart-shell">
        <MichaelSaylorVsBtcTradingViewChart payload={payload} />
      </div>

      <div className="chart-caption-row">
        <div className="chart-legend" aria-label="Chart legend">
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-btc" />
            BTC/USD line
          </span>
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-tweet" />
            Weekly tweet trend
          </span>
        </div>
        <p className="chart-caption">
          Shared x-axis from {formatMonthYear(payload.range.start)} to {formatMonthYear(btcLastIso)}.
          BTC coverage begins in {formatMonthYear(btcFirstIso)}, so the early tweet-only stretch is
          preserved rather than cropped away.
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

function normalizeDateValue(value: string | number): Date | number {
  return typeof value === "string" ? new Date(value) : value;
}
