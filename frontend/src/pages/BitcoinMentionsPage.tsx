import { useEffect, useState } from "react";

import {
  fetchAuthorBitcoinMentions,
  type AuthorBitcoinMentionsResponse,
} from "../api/bitcoinMentions";
import {
  BitcoinMentionsHistoryChart,
  type HoverSnapshot,
} from "../components/BitcoinMentionsHistoryChart";
import {
  type BitcoinMentionsDefinition,
} from "../config/bitcoinMentions";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const wholeDollarFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 0,
  maximumFractionDigits: 0,
});

const integerFormatter = new Intl.NumberFormat("en-US");

const compactNumberFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 6,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 1,
  signDisplay: "always",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
});

type BitcoinMentionsPageProps = {
  bitcoinMentions: BitcoinMentionsDefinition;
};

const fixedBuyAmountUsd = 10;

export function BitcoinMentionsPage({ bitcoinMentions }: BitcoinMentionsPageProps) {
  const [mentionPayload, setMentionPayload] = useState<AuthorBitcoinMentionsResponse | null>(null);
  const [hoverSnapshot, setHoverSnapshot] = useState<HoverSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const detailResponse = await fetchAuthorBitcoinMentions(
          bitcoinMentions.username,
          "bitcoin",
          fixedBuyAmountUsd,
        );

        if (!cancelled) {
          setMentionPayload(detailResponse);
          const latestPoint = detailResponse.btc_series[detailResponse.btc_series.length - 1];
          setHoverSnapshot(
            latestPoint
              ? {
                  btcPriceLabel: formatCurrency(latestPoint.price_usd),
                  dateLabel: formatDateTime(latestPoint.timestamp),
                }
              : null,
          );
          setError(null);
        }
      } catch (loadError) {
        console.error("ChartProject bitcoin mentions request failed", loadError);
        if (!cancelled) {
          setMentionPayload(null);
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unknown Bitcoin mentions request failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    void load();

    return () => {
      cancelled = true;
    };
  }, [bitcoinMentions.username]);

  return (
    <section className="content-stack bitcoin-mentions-page">
      {isLoading ? <p className="status-copy">Loading Bitcoin mentions analysis...</p> : null}
      {error ? <p className="status-copy">{error}</p> : null}

      {mentionPayload ? (
        <>
          <div className="metric-strip">
            <article className="metric-card">
              <p className="metric-label">Bitcoin mentions</p>
              <p className="metric-value">
                {integerFormatter.format(mentionPayload.summary.mention_count)}
              </p>
              <p className="metric-note">
                {integerFormatter.format(mentionPayload.summary.total_tweet_count)} total tweets
                scanned
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Hypothetical invested</p>
              <p className="metric-value">
                {formatCurrency(mentionPayload.summary.total_invested_usd)}
              </p>
              <p className="metric-note">
                Fixed at {formatWholeDollarCurrency(fixedBuyAmountUsd)} per mention
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">BTC accumulated</p>
              <p className="metric-value">
                {compactNumberFormatter.format(mentionPayload.summary.total_btc_accumulated)}
              </p>
              <p className="metric-note">
                From buying {formatWholeDollarCurrency(fixedBuyAmountUsd)} each time
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Current value</p>
              <p className="metric-value">{formatCurrency(mentionPayload.summary.current_value_usd)}</p>
              <p className="metric-note">
                Value today from {formatWholeDollarCurrency(fixedBuyAmountUsd)} per mention
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Portfolio return</p>
              <p className="metric-value">
                {formatPercent(mentionPayload.summary.total_return_pct)}
              </p>
              <p className="metric-note">
                Avg entry {formatCurrency(mentionPayload.summary.average_entry_price_usd)}
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Cheapest mention</p>
              <p className="metric-value">
                {formatCurrency(mentionPayload.summary.lowest_mention_price_usd)}
              </p>
              <p className="metric-note">
                {mentionPayload.summary.best_timed_mention
                  ? formatDateTime(mentionPayload.summary.best_timed_mention.created_at_platform)
                  : "No matches"}
              </p>
            </article>
          </div>

          <article className="panel bitcoin-mentions-panel bitcoin-mentions-panel-wide">
            <div className="chart-shell">
              <BitcoinMentionsHistoryChart
                hoverSnapshot={hoverSnapshot}
                payload={mentionPayload}
                onHoverSnapshotChange={setHoverSnapshot}
              />
            </div>
          </article>
        </>
      ) : null}
    </section>
  );
}

function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  return currencyFormatter.format(value);
}

function formatWholeDollarCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  return wholeDollarFormatter.format(value);
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "N/A";
  }
  return percentFormatter.format(value / 100);
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "N/A";
  }
  return dateTimeFormatter.format(new Date(value));
}
