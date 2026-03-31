import { useEffect, useMemo, useRef, useState } from "react";

import {
  AreaSeries,
  ColorType,
  LineType,
  createChart,
  type AreaData,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";

import {
  fetchAuthorKeywordHeatmap,
  fetchAuthorKeywordTopTweets,
  fetchAuthorKeywordTrend,
  type AuthorKeywordHeatmapResponse,
  type AuthorKeywordTopTweetsResponse,
  type AuthorKeywordTrendResponse,
} from "../api/authorHeatmap";
import { type HeatmapDefinition, getHeatmapLabel } from "../config/heatmaps";

type HeatmapMode = "common" | "rising";
type WordCountFilter = "all" | "1" | "2" | "3";

type AuthorHeatmapPageProps = {
  heatmap: HeatmapDefinition;
};

const integerFormatter = new Intl.NumberFormat("en-US");
const monthLabelFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const tweetTimestampFormatter = new Intl.DateTimeFormat("en-US", {
  hour: "numeric",
  minute: "2-digit",
  hour12: true,
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const chartOptions = {
  layout: {
    background: {
      type: ColorType.Solid,
      color: "rgba(12, 10, 8, 0)",
    },
    textColor: "#d4c5ad",
    attributionLogo: false,
  },
  grid: {
    vertLines: {
      color: "rgba(255, 245, 220, 0.06)",
    },
    horzLines: {
      color: "rgba(255, 245, 220, 0.08)",
    },
  },
  rightPriceScale: {
    borderVisible: false,
  },
  crosshair: {
    vertLine: {
      color: "rgba(255, 178, 64, 0.28)",
      labelBackgroundColor: "#4d2f17",
    },
    horzLine: {
      color: "rgba(118, 199, 255, 0.24)",
      labelBackgroundColor: "#1f3443",
    },
  },
  timeScale: {
    borderVisible: false,
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 4,
    barSpacing: 10,
    minBarSpacing: 0.8,
  },
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
    horzTouchDrag: true,
    vertTouchDrag: false,
  },
  handleScale: {
    axisPressedMouseMove: {
      time: true,
      price: false,
    },
    mouseWheel: true,
    pinch: true,
  },
};

export function AuthorHeatmapPage({ heatmap }: AuthorHeatmapPageProps) {
  const [mode, setMode] = useState<HeatmapMode>("common");
  const [wordCount, setWordCount] = useState<WordCountFilter>("all");
  const [limit] = useState(48);
  const [payload, setPayload] = useState<AuthorKeywordHeatmapResponse | null>(null);
  const [trendPayload, setTrendPayload] = useState<AuthorKeywordTrendResponse | null>(null);
  const [topTweetsPayload, setTopTweetsPayload] = useState<AuthorKeywordTopTweetsResponse | null>(null);
  const [selectedPhrase, setSelectedPhrase] = useState<string | null>(null);
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [isLoadingHeatmap, setIsLoadingHeatmap] = useState(true);
  const [isLoadingTrend, setIsLoadingTrend] = useState(false);
  const [isLoadingTweets, setIsLoadingTweets] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trendError, setTrendError] = useState<string | null>(null);
  const [tweetError, setTweetError] = useState<string | null>(null);
  const heatmapLabel = getHeatmapLabel(heatmap);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function loadHeatmap() {
      setIsLoadingHeatmap(true);
      try {
        const response = await fetchAuthorKeywordHeatmap(
          heatmap.apiBasePath,
          { mode, wordCount, limit },
          controller.signal,
        );
        if (cancelled) {
          return;
        }

        setPayload(response);
        setError(null);
        setSelectedMonth(null);
        setTopTweetsPayload(null);
        setSelectedPhrase((current) => {
          const phraseStillVisible =
            current !== null &&
            response.rows.some((row) => row.normalized_phrase === current);
          return phraseStillVisible ? current : response.rows[0]?.normalized_phrase ?? null;
        });
      } catch (loadError) {
        if (controller.signal.aborted || cancelled) {
          return;
        }

        setPayload(null);
        setTrendPayload(null);
        setTopTweetsPayload(null);
        setSelectedPhrase(null);
        setSelectedMonth(null);
        setError(loadError instanceof Error ? loadError.message : "Unknown heat map fetch failure");
      } finally {
        if (!cancelled) {
          setIsLoadingHeatmap(false);
        }
      }
    }

    void loadHeatmap();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [heatmap.apiBasePath, limit, mode, wordCount]);

  useEffect(() => {
    if (selectedPhrase === null) {
      setTrendPayload(null);
      return;
    }

    const activePhrase = selectedPhrase;
    let cancelled = false;
    const controller = new AbortController();

    async function loadTrend() {
      setIsLoadingTrend(true);
      setTrendError(null);
      setSelectedMonth(null);
      setTopTweetsPayload(null);
      try {
        const response = await fetchAuthorKeywordTrend(
          heatmap.apiBasePath,
          activePhrase,
          controller.signal,
        );
        if (cancelled) {
          return;
        }

        setTrendPayload(response);
      } catch (loadError) {
        if (controller.signal.aborted || cancelled) {
          return;
        }
        setTrendPayload(null);
        setTrendError(loadError instanceof Error ? loadError.message : "Unknown trend fetch failure");
      } finally {
        if (!cancelled) {
          setIsLoadingTrend(false);
        }
      }
    }

    void loadTrend();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [heatmap.apiBasePath, selectedPhrase]);

  useEffect(() => {
    if (selectedPhrase === null || selectedMonth === null) {
      setTopTweetsPayload(null);
      return;
    }

    const activePhrase = selectedPhrase;
    const activeMonth = selectedMonth;
    let cancelled = false;
    const controller = new AbortController();

    async function loadTopTweets() {
      setIsLoadingTweets(true);
      setTweetError(null);
      try {
        const response = await fetchAuthorKeywordTopTweets(
          heatmap.apiBasePath,
          activePhrase,
          activeMonth,
          controller.signal,
        );
        if (cancelled) {
          return;
        }

        setTopTweetsPayload(response);
      } catch (loadError) {
        if (controller.signal.aborted || cancelled) {
          return;
        }
        setTopTweetsPayload(null);
        setTweetError(loadError instanceof Error ? loadError.message : "Unknown top posts fetch failure");
      } finally {
        if (!cancelled) {
          setIsLoadingTweets(false);
        }
      }
    }

    void loadTopTweets();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [heatmap.apiBasePath, selectedMonth, selectedPhrase]);

  const totalVisiblePhraseTweets = useMemo(
    () =>
      payload?.rows.reduce((sum, row) => sum + row.total_matching_tweets, 0) ?? 0,
    [payload],
  );

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace heatmap-workspace">
        <div className="dashboard-workspace-header heatmap-workspace-header">
          <div>
            <p className="chart-control-eyebrow dashboard-eyebrow">Phrase heat map</p>
            <p className="dashboard-subtitle">
              Monthly phrase usage for {heatmapLabel} since August 2020.
            </p>
          </div>
          {isLoadingHeatmap ? <p className="status-copy">Loading {heatmapLabel} heat map...</p> : null}
          {error ? <p className="status-copy">{error}</p> : null}
        </div>

        <div className="metric-strip metric-strip-dashboard heatmap-metric-strip">
          <article className="metric-card">
            <p className="metric-label">Mode</p>
            <p className="metric-value metric-value-compact">{mode === "common" ? "Common" : "Rising"}</p>
            <p className="metric-note">Phrase ranking view</p>
          </article>
          <article className="metric-card">
            <p className="metric-label">Visible phrases</p>
            <p className="metric-value">{integerFormatter.format(payload?.rows.length ?? 0)}</p>
            <p className="metric-note">Top rows in the heat map</p>
          </article>
          <article className="metric-card">
            <p className="metric-label">Months</p>
            <p className="metric-value">{integerFormatter.format(payload?.months.length ?? 0)}</p>
            <p className="metric-note">Dense monthly buckets</p>
          </article>
          <article className="metric-card">
            <p className="metric-label">Visible matches</p>
            <p className="metric-value">{integerFormatter.format(totalVisiblePhraseTweets)}</p>
            <p className="metric-note">Across the selected phrase rows</p>
          </article>
        </div>

        <div className="heatmap-layout">
          <section className="heatmap-panel">
            <div className="heatmap-toolbar">
              <div className="chart-control-card">
                <p className="chart-control-eyebrow">Ranking</p>
                <div className="chart-toggle-group">
                  <button
                    className={`chart-toggle-button${mode === "common" ? " is-active" : ""}`}
                    onClick={() => setMode("common")}
                    type="button"
                  >
                    Common
                  </button>
                  <button
                    className={`chart-toggle-button${mode === "rising" ? " is-active" : ""}`}
                    onClick={() => setMode("rising")}
                    type="button"
                  >
                    Rising
                  </button>
                </div>
              </div>
              <div className="chart-control-card">
                <p className="chart-control-eyebrow">Word Count</p>
                <div className="chart-toggle-group chart-toggle-group-compact">
                  {([
                    ["all", "All"],
                    ["1", "1 word"],
                    ["2", "2 words"],
                    ["3", "3 words"],
                  ] as const).map(([value, label]) => (
                    <button
                      key={value}
                      className={`chart-toggle-button${wordCount === value ? " is-active" : ""}`}
                      onClick={() => setWordCount(value)}
                      type="button"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            <HeatmapGrid
              isLoading={isLoadingHeatmap}
              payload={payload}
              selectedPhrase={selectedPhrase}
              onSelectPhrase={setSelectedPhrase}
            />
          </section>

          <section className="heatmap-detail-stack">
            <div className="chart-control-card heatmap-selection-card">
              <p className="chart-control-eyebrow">Selected Phrase</p>
              <p className="heatmap-selection-title">
                {selectedPhrase ? formatPhraseLabel(selectedPhrase) : "Choose a phrase from the heat map"}
              </p>
              <p className="chart-control-note">
                Click a row or a month cell above to load the full trend below.
              </p>
            </div>

            <div className="chart-shell chart-shell-dashboard heatmap-trend-shell">
              <KeywordTrendChart
                isLoading={isLoadingTrend}
                payload={trendPayload}
                error={trendError}
                selectedMonth={selectedMonth}
                onSelectMonth={setSelectedMonth}
              />
            </div>

            <PhraseTweetPanel
              payload={topTweetsPayload}
              selectedMonth={selectedMonth}
              selectedPhrase={selectedPhrase}
              isLoading={isLoadingTweets}
              error={tweetError}
            />
          </section>
        </div>
      </article>
    </section>
  );
}

function HeatmapGrid({
  isLoading,
  payload,
  selectedPhrase,
  onSelectPhrase,
}: {
  isLoading: boolean;
  payload: AuthorKeywordHeatmapResponse | null;
  selectedPhrase: string | null;
  onSelectPhrase: (phrase: string) => void;
}) {
  const maxCellCount = useMemo(() => {
    if (!payload) {
      return 0;
    }

    return payload.rows.reduce(
      (rowMax, row) =>
        Math.max(rowMax, row.monthly_counts.reduce((cellMax, count) => Math.max(cellMax, count), 0)),
      0,
    );
  }, [payload]);

  if (isLoading && payload === null) {
    return <div className="heatmap-grid-empty">Loading phrase rows...</div>;
  }

  if (payload === null || payload.rows.length === 0) {
    return <div className="heatmap-grid-empty">No phrase rows available for this filter.</div>;
  }

  return (
    <div className="heatmap-grid-shell">
      <table className="heatmap-grid">
        <thead>
          <tr>
            <th className="heatmap-grid-sticky">Phrase</th>
            {payload.months.map((month, index) => (
              <th key={month} title={formatMonthLabel(month)}>
                {index % 3 === 0 ? formatCompactMonthLabel(month) : ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {payload.rows.map((row) => (
            <tr key={row.normalized_phrase} className={selectedPhrase === row.normalized_phrase ? "is-selected" : ""}>
              <th className="heatmap-grid-sticky">
                <button
                  className="heatmap-phrase-button"
                  onClick={() => onSelectPhrase(row.normalized_phrase)}
                  type="button"
                >
                  <span>{formatPhraseLabel(row.phrase)}</span>
                  <span className="heatmap-phrase-total">
                    {integerFormatter.format(row.total_matching_tweets)}
                  </span>
                </button>
              </th>
              {row.monthly_counts.map((count, index) => (
                <td key={`${row.normalized_phrase}-${payload.months[index]}`}>
                  <button
                    className={`heatmap-cell${selectedPhrase === row.normalized_phrase ? " is-row-active" : ""}`}
                    onClick={() => onSelectPhrase(row.normalized_phrase)}
                    style={{
                      backgroundColor: buildHeatmapCellColor(count, maxCellCount),
                    }}
                    title={`${formatPhraseLabel(row.phrase)} · ${formatMonthLabel(payload.months[index])} · ${integerFormatter.format(count)} tweets`}
                    type="button"
                  >
                    <span className="sr-only">
                      {formatPhraseLabel(row.phrase)} {formatMonthLabel(payload.months[index])} {count}
                    </span>
                  </button>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function KeywordTrendChart({
  isLoading,
  payload,
  error,
  selectedMonth,
  onSelectMonth,
}: {
  isLoading: boolean;
  payload: AuthorKeywordTrendResponse | null;
  error: string | null;
  selectedMonth: string | null;
  onSelectMonth: (monthStart: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hoverLabel, setHoverLabel] = useState<string>("Hover the chart");
  const [hoverValue, setHoverValue] = useState<string>("Monthly count");
  const seriesData = useMemo<AreaData<Time>[]>(
    () =>
      payload?.series.map((point) => ({
        time: toBusinessDay(point.period_start),
        value: point.matching_tweet_count,
      })) ?? [],
    [payload],
  );

  useEffect(() => {
    if (!payload) {
      return;
    }
    const latestPoint = payload.series[payload.series.length - 1];
    if (!latestPoint) {
      return;
    }

    setHoverLabel(formatMonthLabel(latestPoint.period_start));
    setHoverValue(`${integerFormatter.format(latestPoint.matching_tweet_count)} tweets`);
  }, [payload]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || payload === null) {
      return;
    }

    const chart = createChart(container, {
      ...chartOptions,
      width: container.clientWidth,
      height: container.clientHeight,
    });

    const series = chart.addSeries(AreaSeries, {
      lineColor: "#ffb240",
      topColor: "rgba(255, 178, 64, 0.32)",
      bottomColor: "rgba(255, 178, 64, 0.04)",
      lineWidth: 3,
      lineType: LineType.Curved,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBorderWidth: 2,
      crosshairMarkerBorderColor: "#ffb240",
      crosshairMarkerBackgroundColor: "#17130f",
    });

    series.setData(seriesData);
    chart.timeScale().fitContent();

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        const latestPoint = payload.series[payload.series.length - 1];
        if (latestPoint) {
          setHoverLabel(formatMonthLabel(latestPoint.period_start));
          setHoverValue(`${integerFormatter.format(latestPoint.matching_tweet_count)} tweets`);
        }
        return;
      }

      const matchingPoint = findTrendPointForTime(param.time, payload.series);
      if (!matchingPoint) {
        return;
      }

      setHoverLabel(formatMonthLabel(matchingPoint.period_start));
      setHoverValue(`${integerFormatter.format(matchingPoint.matching_tweet_count)} tweets`);
    };

    const handleClick = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        return;
      }

      const matchingPoint = findTrendPointForTime(param.time, payload.series);
      if (!matchingPoint) {
        return;
      }

      onSelectMonth(matchingPoint.period_start);
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);
    chart.subscribeClick(handleClick);

    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.unsubscribeClick(handleClick);
      chart.remove();
    };
  }, [onSelectMonth, payload, seriesData]);

  return (
    <div className="heatmap-trend-layout">
      <div className="heatmap-trend-sidebar">
        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Trend</p>
          <p className="heatmap-selection-title">
            {payload ? formatPhraseLabel(payload.phrase) : "Phrase trend"}
          </p>
          <p className="chart-control-note">
            Full monthly history since August 2020. Click a month to load the top liked posts.
          </p>
        </div>
        <div className="chart-hover-item">
          <span className="chart-hover-label">Hover month</span>
          <span className="chart-hover-value">{hoverLabel}</span>
        </div>
        <div className="chart-hover-item">
          <span className="chart-hover-label">Matching tweets</span>
          <span className="chart-hover-value">{hoverValue}</span>
        </div>
        <div className="chart-hover-item">
          <span className="chart-hover-label">Selected month</span>
          <span className="chart-hover-value">
            {selectedMonth ? formatMonthLabel(selectedMonth) : "Click a month"}
          </span>
        </div>
      </div>

      <div className="chart-stage">
        {isLoading ? <div className="heatmap-grid-empty">Loading phrase trend...</div> : null}
        {!isLoading && error ? <div className="heatmap-grid-empty">{error}</div> : null}
        {!isLoading && !error && payload ? (
          <div className="tradingview-chart heatmap-trend-chart" ref={containerRef} />
        ) : null}
      </div>
    </div>
  );
}

function PhraseTweetPanel({
  payload,
  selectedMonth,
  selectedPhrase,
  isLoading,
  error,
}: {
  payload: AuthorKeywordTopTweetsResponse | null;
  selectedMonth: string | null;
  selectedPhrase: string | null;
  isLoading: boolean;
  error: string | null;
}) {
  return (
    <section className="top-tweet-card phrase-tweet-panel">
      <p className="top-tweet-eyebrow">Phrase Drilldown</p>
      <p className="top-tweet-week">
        {selectedPhrase ? formatPhraseLabel(selectedPhrase) : "Select a phrase"}{" "}
        {selectedMonth ? `· ${formatMonthLabel(selectedMonth)}` : ""}
      </p>

      {!selectedPhrase ? (
        <p className="top-tweet-status">Select a phrase in the heat map to inspect matching tweets.</p>
      ) : null}

      {selectedPhrase && !selectedMonth ? (
        <p className="top-tweet-status">Click a month on the trend chart to load the top liked tweets.</p>
      ) : null}

      {isLoading ? <p className="top-tweet-status">Loading matching tweets...</p> : null}
      {error ? <p className="top-tweet-status">{error}</p> : null}
      {payload && payload.tweets.length === 0 ? (
        <p className="top-tweet-status">No matching tweets found for that month.</p>
      ) : null}

      {payload?.tweets.map((tweet) => (
        <div key={tweet.platform_tweet_id} className="tweet-preview-card phrase-tweet-card">
          <div className="tweet-preview-header">
            <div className="tweet-preview-identity">
              {payload.subject.profile_image_url ? (
                <img
                  alt={payload.subject.display_name ?? payload.subject.username}
                  className="tweet-preview-avatar"
                  src={payload.subject.profile_image_url}
                />
              ) : (
                <div className="tweet-preview-avatar tweet-preview-avatar-fallback" aria-hidden="true">
                  {buildAvatarInitials(payload.subject)}
                </div>
              )}
              <div className="tweet-preview-author-block">
                <p className="tweet-preview-name">
                  {payload.subject.display_name ?? payload.subject.username}
                </p>
                <p className="tweet-preview-handle">@{payload.subject.username}</p>
              </div>
            </div>
          </div>
          <p className="tweet-preview-timestamp">
            {tweetTimestampFormatter.format(new Date(tweet.created_at_platform))}
          </p>
          <p className="top-tweet-text">{tweet.text}</p>
          <div className="tweet-preview-actions" aria-label="Post engagement">
            <span className="tweet-action-stat is-accent">Likes {formatMetricValue(tweet.like_count)}</span>
            <span className="tweet-action-stat">Replies {formatMetricValue(tweet.reply_count)}</span>
            <span className="tweet-action-stat">Reposts {formatMetricValue(tweet.repost_count)}</span>
            <span className="tweet-action-stat">Bookmarks {formatMetricValue(tweet.bookmark_count)}</span>
          </div>
        </div>
      ))}
    </section>
  );
}

function buildHeatmapCellColor(count: number, maxCount: number): string {
  if (count === 0 || maxCount === 0) {
    return "rgba(255, 245, 220, 0.04)";
  }

  const intensity = Math.sqrt(count / maxCount);
  const alpha = 0.14 + intensity * 0.72;
  return `rgba(255, 178, 64, ${alpha.toFixed(3)})`;
}

function buildAvatarInitials(subject: {
  display_name: string | null;
  username: string;
}): string {
  const source = subject.display_name ?? subject.username;
  return source
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((segment) => segment.charAt(0).toUpperCase())
    .join("");
}

function formatPhraseLabel(value: string): string {
  const uppercaseTokens = new Set(["btc", "mstr", "strc", "strd", "strf", "strk", "usd", "etf", "ai"]);
  return value
    .split(" ")
    .map((token) => (uppercaseTokens.has(token) ? token.toUpperCase() : token))
    .join(" ");
}

function formatMonthLabel(value: string): string {
  return monthLabelFormatter.format(new Date(value));
}

function formatCompactMonthLabel(value: string): string {
  const formatted = formatMonthLabel(value);
  return formatted.replace(" 20", " ");
}

function formatMetricValue(value: number | null): string {
  return integerFormatter.format(value ?? 0);
}

function toBusinessDay(value: string): Time {
  return value.slice(0, 10) as Time;
}

function findTrendPointForTime(
  time: Time,
  series: AuthorKeywordTrendResponse["series"],
): AuthorKeywordTrendResponse["series"][number] | null {
  const businessDay =
    typeof time === "string"
      ? time
      : typeof time === "object" && "year" in time
        ? `${time.year}-${`${time.month}`.padStart(2, "0")}-${`${time.day}`.padStart(2, "0")}`
        : null;
  if (businessDay === null) {
    return null;
  }
  return series.find((point) => point.period_start.startsWith(businessDay)) ?? null;
}
