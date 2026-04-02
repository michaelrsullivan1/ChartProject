import { useEffect, useState } from "react";

import {
  fetchAuthorBitcoinMentions,
  type AuthorBitcoinMentionsResponse,
} from "../api/bitcoinMentions";
import { BitcoinMentionsHistoryChart } from "../components/BitcoinMentionsHistoryChart";
import {
  type BitcoinMentionsDefinition,
} from "../config/bitcoinMentions";

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
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
                Fixed at {formatCurrency(fixedBuyAmountUsd)} per mention
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">BTC accumulated</p>
              <p className="metric-value">
                {compactNumberFormatter.format(mentionPayload.summary.total_btc_accumulated)}
              </p>
              <p className="metric-note">
                From buying {formatCurrency(fixedBuyAmountUsd)} each time
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Current value</p>
              <p className="metric-value">{formatCurrency(mentionPayload.summary.current_value_usd)}</p>
              <p className="metric-note">
                Value today from {formatCurrency(fixedBuyAmountUsd)} per mention
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
            <div className="bitcoin-mentions-panel-header">
              <div>
                <p className="eyebrow dashboard-eyebrow">Price History</p>
                <h2>BTC price with one dot per matched tweet</h2>
              </div>
              <p className="status-copy">
                Click near a dot to load the closest matching tweet in the side panel.
              </p>
            </div>
            <div className="chart-shell">
              <BitcoinMentionsHistoryChart payload={mentionPayload} />
            </div>
          </article>

          <div className="bitcoin-mentions-grid">
            <article className="panel bitcoin-mentions-panel">
              <div className="bitcoin-mentions-panel-header">
                <div>
                  <p className="eyebrow dashboard-eyebrow">Cheapest Entries</p>
                  <h2>Lowest-price Bitcoin mentions</h2>
                </div>
                <p className="status-copy">
                  Best-timed entries for {mentionPayload.subject.display_name ?? mentionPayload.subject.username}
                </p>
              </div>
              {mentionPayload.cheapest_mentions.length > 0 ? (
                <div className="bitcoin-mini-list">
                  {mentionPayload.cheapest_mentions.map((mention) => (
                    <article key={mention.platform_tweet_id} className="bitcoin-mini-card">
                      <div className="bitcoin-mini-card-topline">
                        <strong>{formatCurrency(mention.btc_price_usd)}</strong>
                        <span>{formatDateTime(mention.created_at_platform)}</span>
                      </div>
                      <p className="bitcoin-mini-card-copy">{mention.text}</p>
                      <p className="bitcoin-mini-card-meta">
                        {formatCurrency(mention.hypothetical_current_value_usd)} today from{" "}
                        {formatCurrency(mention.hypothetical_buy_amount_usd)}.{" "}
                        {mention.url ? (
                          <a href={mention.url} rel="noreferrer" target="_blank">
                            Open tweet
                          </a>
                        ) : null}
                      </p>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="status-copy">No phrase-matching mentions were found for this author.</p>
              )}
            </article>
          </div>
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
