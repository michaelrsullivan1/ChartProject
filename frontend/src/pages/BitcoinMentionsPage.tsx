import { useEffect, useState, type FormEvent } from "react";

import {
  fetchAuthorBitcoinMentions,
  fetchBitcoinMentionsLeaderboard,
  type AuthorBitcoinMentionsResponse,
  type BitcoinMention,
  type BitcoinMentionsLeaderboardResponse,
} from "../api/bitcoinMentions";
import { BitcoinMentionsHistoryChart } from "../components/BitcoinMentionsHistoryChart";
import { getOverviewLabel, overviewDefinitions } from "../config/overviews";

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

type MentionSortMode = "date-desc" | "price-asc" | "return-desc" | "likes-desc";

const authorOptions = overviewDefinitions.map((overview) => ({
  label: getOverviewLabel(overview),
  username: overview.username,
}));

export function BitcoinMentionsPage() {
  const [selectedUsername, setSelectedUsername] = useState(authorOptions[0]?.username ?? "");
  const [draftPhrase, setDraftPhrase] = useState("bitcoin");
  const [draftBuyAmount, setDraftBuyAmount] = useState("10");
  const [submittedPhrase, setSubmittedPhrase] = useState("bitcoin");
  const [submittedBuyAmount, setSubmittedBuyAmount] = useState(10);
  const [mentionPayload, setMentionPayload] = useState<AuthorBitcoinMentionsResponse | null>(null);
  const [leaderboardPayload, setLeaderboardPayload] =
    useState<BitcoinMentionsLeaderboardResponse | null>(null);
  const [sortMode, setSortMode] = useState<MentionSortMode>("price-asc");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!selectedUsername) {
      return;
    }

    let cancelled = false;

    async function load() {
      try {
        const usernames = authorOptions.map((author) => author.username);
        const [detailResponse, leaderboardResponse] = await Promise.all([
          fetchAuthorBitcoinMentions(selectedUsername, submittedPhrase, submittedBuyAmount),
          fetchBitcoinMentionsLeaderboard(usernames, submittedPhrase, submittedBuyAmount),
        ]);

        if (!cancelled) {
          setMentionPayload(detailResponse);
          setLeaderboardPayload(leaderboardResponse);
          setError(null);
        }
      } catch (loadError) {
        console.error("ChartProject bitcoin mentions request failed", loadError);
        if (!cancelled) {
          setMentionPayload(null);
          setLeaderboardPayload(null);
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
  }, [selectedUsername, submittedBuyAmount, submittedPhrase]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const normalizedPhrase = draftPhrase.trim();
    const parsedBuyAmount = Number(draftBuyAmount);
    if (!normalizedPhrase) {
      setError("Phrase must not be empty.");
      return;
    }
    if (!Number.isFinite(parsedBuyAmount) || parsedBuyAmount <= 0) {
      setError("Buy amount must be greater than zero.");
      return;
    }

    setSubmittedPhrase(normalizedPhrase);
    setSubmittedBuyAmount(parsedBuyAmount);
  }

  const displayedMentions = sortMentions(mentionPayload?.mentions ?? [], sortMode);

  return (
    <section className="content-stack bitcoin-mentions-page">
      <article className="panel panel-accent bitcoin-mentions-hero">
        <div>
          <p className="eyebrow dashboard-eyebrow">Bitcoin Mentions</p>
          <h2 className="bitcoin-mentions-title">Every time an author talked about Bitcoin</h2>
          <p className="dashboard-subtitle bitcoin-mentions-subtitle">
            Exact tweet timestamps, paired with the stored BTC daily UTC close for that date, then
            rolled forward to today as a simple “buy {formatCurrency(submittedBuyAmount)} every
            time” model.
          </p>
        </div>

        <form className="bitcoin-mentions-controls" onSubmit={handleSubmit}>
          <label className="bitcoin-mentions-field">
            <span>Author</span>
            <select
              value={selectedUsername}
              onChange={(event) => setSelectedUsername(event.target.value)}
            >
              {authorOptions.map((author) => (
                <option key={author.username} value={author.username}>
                  {author.label}
                </option>
              ))}
            </select>
          </label>

          <label className="bitcoin-mentions-field">
            <span>Phrase</span>
            <input
              value={draftPhrase}
              onChange={(event) => setDraftPhrase(event.target.value)}
              placeholder="bitcoin"
              type="text"
            />
          </label>

          <label className="bitcoin-mentions-field">
            <span>Buy per mention</span>
            <input
              value={draftBuyAmount}
              onChange={(event) => setDraftBuyAmount(event.target.value)}
              inputMode="decimal"
              min="0.01"
              step="0.01"
              type="number"
            />
          </label>

          <button className="bitcoin-mentions-submit" type="submit">
            Recalculate
          </button>
        </form>

        {mentionPayload ? (
          <p className="status-copy bitcoin-mentions-methodology">
            {mentionPayload.pricing.methodology} Current BTC reference:{" "}
            <strong>{formatCurrency(mentionPayload.pricing.current_price_usd)}</strong> as of{" "}
            {formatDateTime(mentionPayload.pricing.current_price_as_of)}.
          </p>
        ) : null}
        {isLoading ? <p className="status-copy">Loading Bitcoin mentions analysis...</p> : null}
        {error ? <p className="status-copy">{error}</p> : null}
      </article>

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
                {formatCurrency(mentionPayload.summary.buy_amount_usd)} per mention
              </p>
            </article>
            <article className="metric-card">
              <p className="metric-label">BTC accumulated</p>
              <p className="metric-value">
                {compactNumberFormatter.format(mentionPayload.summary.total_btc_accumulated)}
              </p>
              <p className="metric-note">Rolled forward to current BTC price</p>
            </article>
            <article className="metric-card">
              <p className="metric-label">Current value</p>
              <p className="metric-value">{formatCurrency(mentionPayload.summary.current_value_usd)}</p>
              <p className="metric-note">
                Net {formatCurrency(mentionPayload.summary.total_return_usd)}
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
            <article className="panel bitcoin-mentions-panel bitcoin-mentions-panel-wide">
              <div className="bitcoin-mentions-panel-header">
                <div>
                  <p className="eyebrow dashboard-eyebrow">Leaderboard</p>
                  <h2>Who tends to mention Bitcoin at lower prices?</h2>
                </div>
                <p className="status-copy">
                  Ranked by average BTC entry price across matched mentions.
                </p>
              </div>
              {leaderboardPayload ? (
                <div className="bitcoin-table-shell">
                  <table className="bitcoin-table">
                    <thead>
                      <tr>
                        <th>Author</th>
                        <th>Mentions</th>
                        <th>Avg Entry</th>
                        <th>Best Mention</th>
                        <th>Invested</th>
                        <th>Current Value</th>
                        <th>Return</th>
                      </tr>
                    </thead>
                    <tbody>
                      {leaderboardPayload.leaderboard.map((row) => {
                        const isActive = row.subject.username === mentionPayload.subject.username;
                        return (
                          <tr key={row.subject.username} className={isActive ? "is-active" : ""}>
                            <td>{row.subject.display_name ?? row.subject.username}</td>
                            <td>{integerFormatter.format(row.mention_count)}</td>
                            <td>{formatCurrency(row.average_entry_price_usd)}</td>
                            <td>{formatCurrency(row.lowest_mention_price_usd)}</td>
                            <td>{formatCurrency(row.total_invested_usd)}</td>
                            <td>{formatCurrency(row.current_value_usd)}</td>
                            <td>{formatPercent(row.total_return_pct)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="status-copy">
                  Leaderboard data is still loading or unavailable for this phrase.
                </p>
              )}
            </article>

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

          <article className="panel bitcoin-mentions-panel">
            <div className="bitcoin-mentions-panel-header">
              <div>
                <p className="eyebrow dashboard-eyebrow">Full History</p>
                <h2>Every matched mention</h2>
              </div>
              <label className="bitcoin-mentions-inline-field">
                <span>Sort by</span>
                <select value={sortMode} onChange={(event) => setSortMode(event.target.value as MentionSortMode)}>
                  <option value="price-asc">Lowest BTC price</option>
                  <option value="date-desc">Most recent</option>
                  <option value="return-desc">Highest return today</option>
                  <option value="likes-desc">Most likes</option>
                </select>
              </label>
            </div>

            {displayedMentions.length > 0 ? (
              <div className="bitcoin-table-shell">
                <table className="bitcoin-table bitcoin-table-detail">
                  <thead>
                    <tr>
                      <th>When</th>
                      <th>BTC Price</th>
                      <th>Value Today</th>
                      <th>Return</th>
                      <th>Likes</th>
                      <th>Tweet</th>
                    </tr>
                  </thead>
                  <tbody>
                    {displayedMentions.map((mention) => (
                      <tr key={mention.platform_tweet_id}>
                        <td>{formatDateTime(mention.created_at_platform)}</td>
                        <td>{formatCurrency(mention.btc_price_usd)}</td>
                        <td>{formatCurrency(mention.hypothetical_current_value_usd)}</td>
                        <td>{formatPercent(mention.price_change_since_tweet_pct)}</td>
                        <td>{integerFormatter.format(mention.like_count ?? 0)}</td>
                        <td>
                          <div className="bitcoin-tweet-cell">
                            <p>{mention.text}</p>
                            {mention.url ? (
                              <a href={mention.url} rel="noreferrer" target="_blank">
                                Open tweet
                              </a>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="status-copy">No phrase-matching mentions were found for this author.</p>
            )}
          </article>
        </>
      ) : null}
    </section>
  );
}

function sortMentions(mentions: BitcoinMention[], sortMode: MentionSortMode): BitcoinMention[] {
  const items = [...mentions];
  if (sortMode === "date-desc") {
    items.sort((left, right) => right.created_at_platform.localeCompare(left.created_at_platform));
    return items;
  }
  if (sortMode === "return-desc") {
    items.sort(
      (left, right) => right.price_change_since_tweet_pct - left.price_change_since_tweet_pct,
    );
    return items;
  }
  if (sortMode === "likes-desc") {
    items.sort((left, right) => (right.like_count ?? 0) - (left.like_count ?? 0));
    return items;
  }
  items.sort((left, right) => left.btc_price_usd - right.btc_price_usd);
  return items;
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
