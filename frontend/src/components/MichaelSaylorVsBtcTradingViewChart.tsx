import { useEffect, useMemo, useRef, useState } from "react";

import {
  AreaSeries,
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type AreaData,
  type LineData,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";

import type { MichaelSaylorVsBtcResponse } from "../api/michaelSaylorVsBtc";
import {
  fetchMichaelSaylorTopLikedTweet,
  type MichaelSaylorTopLikedTweetResponse,
} from "../api/michaelSaylorTopLikedTweet";

type MichaelSaylorVsBtcTradingViewChartProps = {
  payload: MichaelSaylorVsBtcResponse;
};

type HoverSnapshot = {
  dateLabel: string;
  btcPriceLabel: string;
  tweetCountLabel: string;
  hasBtcValue: boolean;
};

type TopTweetPanelState = {
  status: "idle" | "waiting" | "loading" | "loaded" | "error";
  weekStart: string | null;
  response: MichaelSaylorTopLikedTweetResponse | null;
  error: string | null;
};

type SelectedWeek = {
  weekStart: string;
  tweetCount: number;
};

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const integerFormatter = new Intl.NumberFormat("en-US");

const fullDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const shortDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
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

const compactCountFormatter = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
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
  leftPriceScale: {
    visible: false,
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
    barSpacing: 8.5,
    minBarSpacing: 1.5,
  },
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
    horzTouchDrag: true,
    vertTouchDrag: false,
  },
  handleScale: {
    axisPressedMouseMove: true,
    mouseWheel: true,
    pinch: true,
  },
};

export function MichaelSaylorVsBtcTradingViewChart({
  payload,
}: MichaelSaylorVsBtcTradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const topTweetCacheRef = useRef(new Map<string, MichaelSaylorTopLikedTweetResponse>());
  const btcSeriesData = useMemo(() => buildBtcSeries(payload), [payload]);
  const tweetSeriesData = useMemo(() => buildTweetSeries(payload), [payload]);
  const [hoverSnapshot, setHoverSnapshot] = useState<HoverSnapshot>(() =>
    buildLatestHoverSnapshot(btcSeriesData, tweetSeriesData),
  );
  const [selectedWeek, setSelectedWeek] = useState<SelectedWeek | null>(null);
  const [topTweetPanel, setTopTweetPanel] = useState<TopTweetPanelState>({
    status: "idle",
    weekStart: null,
    response: null,
    error: null,
  });

  useEffect(() => {
    setHoverSnapshot(buildLatestHoverSnapshot(btcSeriesData, tweetSeriesData));
  }, [btcSeriesData, tweetSeriesData]);

  useEffect(() => {
    if (selectedWeek === null) {
      return;
    }

    const activeWeek = selectedWeek;

    if (activeWeek.tweetCount === 0) {
      setTopTweetPanel({
        status: "loaded",
        weekStart: activeWeek.weekStart,
        response: null,
        error: null,
      });
      return;
    }

    const cached = topTweetCacheRef.current.get(activeWeek.weekStart);
    if (cached) {
      setTopTweetPanel({
        status: "loaded",
        weekStart: activeWeek.weekStart,
        response: cached,
        error: null,
      });
      return;
    }

    const controller = new AbortController();

    async function loadTopTweet() {
      setTopTweetPanel({
        status: "loading",
        weekStart: activeWeek.weekStart,
        response: null,
        error: null,
      });

      try {
        const response = await fetchMichaelSaylorTopLikedTweet(
          activeWeek.weekStart,
          controller.signal,
        );
        topTweetCacheRef.current.set(activeWeek.weekStart, response);
        setTopTweetPanel({
          status: "loaded",
          weekStart: activeWeek.weekStart,
          response,
          error: null,
        });
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        setTopTweetPanel({
          status: "error",
          weekStart: activeWeek.weekStart,
          response: null,
          error:
            error instanceof Error
              ? error.message
              : "Unknown top liked tweet fetch failure",
        });
      }
    }

    void loadTopTweet();

    return () => {
      controller.abort();
    };
  }, [selectedWeek]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = createChart(container, {
      ...chartOptions,
      width: container.clientWidth,
      height: container.clientHeight,
    });

    const btcSeries = chart.addSeries(LineSeries, {
      title: "BTC/USD",
      color: "#76c7ff",
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      lastValueVisible: true,
      priceLineVisible: true,
      priceLineColor: "#76c7ff",
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    const tweetSeries = chart.addSeries(
      AreaSeries,
      {
        title: "Tweets / week",
        lineColor: "#ffb240",
        topColor: "rgba(255, 178, 64, 0.22)",
        bottomColor: "rgba(255, 178, 64, 0.02)",
        lineWidth: 3,
        lineType: LineType.Curved,
        lastValueVisible: true,
        priceLineVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        priceFormat: {
          type: "volume",
        },
      },
      1,
    );

    btcSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.08,
      },
    });

    tweetSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.16,
        bottom: 0,
      },
    });

    btcSeries.setData(btcSeriesData);
    tweetSeries.setData(tweetSeriesData);

    const panes = chart.panes();
    panes[0]?.setHeight(320);
    panes[1]?.setHeight(180);

    chart.timeScale().fitContent();

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        setHoverSnapshot(buildLatestHoverSnapshot(btcSeriesData, tweetSeriesData));
        return;
      }

      const btcPoint = param.seriesData.get(btcSeries) as LineData<Time> | undefined;
      const tweetPoint = findTweetPointForTime(param.time, tweetSeriesData);

      setHoverSnapshot({
        dateLabel: formatTimeLabel(param.time),
        btcPriceLabel:
          btcPoint?.value !== undefined ? currencyFormatter.format(btcPoint.value) : "No BTC data",
        tweetCountLabel:
          tweetPoint?.value !== undefined
            ? `${integerFormatter.format(tweetPoint.value)} tweets`
            : "No tweet bucket",
        hasBtcValue: btcPoint?.value !== undefined,
      });
    };

    const handleClick = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        return;
      }

      const tweetPoint = findTweetPointForTime(param.time, tweetSeriesData);
      if (!tweetPoint || typeof tweetPoint.time !== "string") {
        return;
      }

      const weekStart = tweetPoint.time;

      setSelectedWeek({
        weekStart,
        tweetCount: tweetPoint.value,
      });

      setTopTweetPanel((current) => ({
        status: current.weekStart === weekStart ? current.status : "waiting",
        weekStart,
        response: current.weekStart === weekStart ? current.response : null,
        error: null,
      }));
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);
    chart.subscribeClick(handleClick);

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });

    resizeObserver.observe(container);

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.unsubscribeClick(handleClick);
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [btcSeriesData, tweetSeriesData]);

  return (
    <div className="tradingview-chart-shell">
      <div className="chart-stage">
        <div className="tradingview-chart" ref={containerRef} />
      </div>

      <aside className="chart-sidebar">
        <div className="chart-hover-strip" aria-live="polite">
          <div className="chart-hover-item">
            <span className="chart-hover-label">Date</span>
            <span className="chart-hover-value">{hoverSnapshot.dateLabel}</span>
          </div>
          <div className="chart-hover-item">
            <span className="chart-hover-label">BTC</span>
            <span
              className={`chart-hover-value${hoverSnapshot.hasBtcValue ? "" : " is-muted"}`}
            >
              {hoverSnapshot.btcPriceLabel}
            </span>
          </div>
          <div className="chart-hover-item">
            <span className="chart-hover-label">Tweets That Week</span>
            <span className="chart-hover-value">{hoverSnapshot.tweetCountLabel}</span>
          </div>
        </div>

        <TopLikedTweetCard
          selectedWeek={selectedWeek}
          topTweetPanel={topTweetPanel}
        />
      </aside>
    </div>
  );
}

function TopLikedTweetCard({
  selectedWeek,
  topTweetPanel,
}: {
  selectedWeek: SelectedWeek | null;
  topTweetPanel: TopTweetPanelState;
}) {
  const topTweet = topTweetPanel.response?.top_tweet ?? null;
  const weekStart = topTweetPanel.weekStart ?? selectedWeek?.weekStart ?? null;
  const tweetUrl = topTweet !== null ? topTweet.url ?? buildTweetUrl(topTweetPanel.response) : null;

  if (topTweet !== null && tweetUrl !== null) {
    return (
      <a
        className="top-tweet-card top-tweet-card-link"
        href={tweetUrl}
        rel="noreferrer"
        target="_blank"
      >
        <TopLikedTweetCardBody
          selectedWeek={selectedWeek}
          topTweetPanel={topTweetPanel}
        />
      </a>
    );
  }

  return (
    <article className="top-tweet-card">
      <TopLikedTweetCardBody
        selectedWeek={selectedWeek}
        topTweetPanel={topTweetPanel}
      />
    </article>
  );
}

function TopLikedTweetCardBody({
  selectedWeek,
  topTweetPanel,
}: {
  selectedWeek: SelectedWeek | null;
  topTweetPanel: TopTweetPanelState;
}) {
  const topTweet = topTweetPanel.response?.top_tweet ?? null;
  const weekStart = topTweetPanel.weekStart ?? selectedWeek?.weekStart ?? null;

  return (
    <>
      <p className="top-tweet-eyebrow">Top Liked Tweet For Selected Week</p>
      <p className="top-tweet-week">
        {weekStart ? `Week of ${formatWeekLabel(weekStart)}` : "Click a week to inspect it"}
      </p>

      {topTweetPanel.status === "idle" ? (
        <p className="top-tweet-status">
          Click on the chart to lock a week and load the most liked tweet from that selected week.
        </p>
      ) : null}

      {topTweetPanel.status === "waiting" ? (
        <p className="top-tweet-status">Week selected. Loading top liked tweet for that week.</p>
      ) : null}

      {topTweetPanel.status === "loading" ? (
        <p className="top-tweet-status">Loading top liked tweet from the selected week...</p>
      ) : null}

      {topTweetPanel.status === "error" ? (
        <p className="top-tweet-status">{topTweetPanel.error ?? "Top tweet request failed."}</p>
      ) : null}

      {topTweetPanel.status === "loaded" && (selectedWeek?.tweetCount ?? 0) === 0 ? (
        <p className="top-tweet-status">No tweets were authored in this selected week.</p>
      ) : null}

      {topTweetPanel.status === "loaded" && (selectedWeek?.tweetCount ?? 0) !== 0 && topTweet === null ? (
        <p className="top-tweet-status">No top liked tweet was found for this selected week.</p>
      ) : null}

      {topTweet !== null ? (
        <>
          <div className="tweet-preview-card">
            <div className="tweet-preview-header">
              <div>
                <p className="tweet-preview-name">
                  {topTweetPanel.response?.subject.display_name ??
                    topTweetPanel.response?.subject.username ??
                    "Michael Saylor"}
                </p>
                <p className="tweet-preview-handle">
                  @{topTweetPanel.response?.subject.username ?? "saylor"}
                </p>
              </div>
            </div>

            <p className="top-tweet-text">{topTweet.text}</p>

            <p className="tweet-preview-timestamp">
              {formatTweetTimestamp(topTweet.created_at_platform)}
            </p>

            <div className="tweet-preview-actions" aria-label="Tweet engagement">
              <TweetActionStat
                icon="reply"
                label="Replies"
                value={topTweet.reply_count}
              />
              <TweetActionStat
                icon="repost"
                label="Reposts"
                value={topTweet.repost_count}
              />
              <TweetActionStat
                icon="like"
                label="Likes"
                value={topTweet.like_count}
                tone="accent"
              />
              <TweetActionStat
                icon="bookmark"
                label="Bookmarks"
                value={topTweet.bookmark_count}
              />
            </div>
          </div>
        </>
      ) : null}
    </>
  );
}

function TweetActionStat({
  icon,
  label,
  value,
  tone = "default",
}: {
  icon: "reply" | "repost" | "like" | "bookmark";
  label: string;
  value: number | null;
  tone?: "default" | "accent";
}) {
  return (
    <span
      aria-label={`${label}: ${value ?? 0}`}
      className={`tweet-action-stat${tone === "accent" ? " is-accent" : ""}`}
      title={label}
    >
      <span className="tweet-action-icon" aria-hidden="true">
        {renderActionIcon(icon)}
      </span>
      <span>{formatCompactCount(value ?? 0)}</span>
    </span>
  );
}

function buildBtcSeries(payload: MichaelSaylorVsBtcResponse): LineData<Time>[] {
  return payload.btc_series.map((point) => ({
    time: toBusinessDay(point.timestamp),
    value: point.price_usd,
  }));
}

function buildTweetSeries(payload: MichaelSaylorVsBtcResponse): AreaData<Time>[] {
  return payload.tweet_series.map((point) => ({
    time: toBusinessDay(point.period_start),
    value: point.tweet_count,
  }));
}

function buildLatestHoverSnapshot(
  btcSeriesData: LineData<Time>[],
  tweetSeriesData: AreaData<Time>[],
): HoverSnapshot {
  const latestBtc = btcSeriesData[btcSeriesData.length - 1];
  const latestTweets = tweetSeriesData[tweetSeriesData.length - 1];
  const time = latestBtc?.time ?? latestTweets?.time ?? "1970-01-01";

  return {
    dateLabel: formatTimeLabel(time),
    btcPriceLabel:
      latestBtc?.value !== undefined ? currencyFormatter.format(latestBtc.value) : "No BTC data",
    tweetCountLabel:
      latestTweets?.value !== undefined
        ? `${integerFormatter.format(latestTweets.value)} tweets`
        : "No tweet bucket",
    hasBtcValue: latestBtc?.value !== undefined,
  };
}

function findTweetPointForTime(
  time: Time,
  tweetSeriesData: AreaData<Time>[],
): AreaData<Time> | undefined {
  const hoveredDate = normalizeTime(time).getTime();

  for (let index = tweetSeriesData.length - 1; index >= 0; index -= 1) {
    const point = tweetSeriesData[index];
    const pointStart = normalizeTime(point.time).getTime();
    const pointEnd = pointStart + 7 * 24 * 60 * 60 * 1000;

    if (hoveredDate >= pointStart && hoveredDate < pointEnd) {
      return point;
    }
  }

  return undefined;
}

function formatTimeLabel(time: Time): string {
  return fullDateFormatter.format(normalizeTime(time));
}

function formatWeekLabel(value: string): string {
  return shortDateFormatter.format(new Date(`${value}T00:00:00Z`));
}

function formatTweetTimestamp(value: string): string {
  const parts = tweetTimestampFormatter.formatToParts(new Date(value));
  const hour = parts.find((part) => part.type === "hour")?.value ?? "";
  const minute = parts.find((part) => part.type === "minute")?.value ?? "";
  const dayPeriod = parts.find((part) => part.type === "dayPeriod")?.value?.toUpperCase() ?? "";
  const month = parts.find((part) => part.type === "month")?.value ?? "";
  const day = parts.find((part) => part.type === "day")?.value ?? "";
  const year = parts.find((part) => part.type === "year")?.value ?? "";

  return `${hour}:${minute} ${dayPeriod} · ${month} ${day}, ${year}`;
}

function formatCompactCount(value: number): string {
  if (value < 10_000) {
    return integerFormatter.format(value);
  }

  return compactCountFormatter.format(value).toUpperCase();
}

function normalizeTime(time: Time): Date {
  if (typeof time === "string") {
    return new Date(`${time}T00:00:00Z`);
  }

  if (typeof time === "number") {
    return new Date(time * 1000);
  }

  return new Date(Date.UTC(time.year, time.month - 1, time.day));
}

function toBusinessDay(value: string): string {
  return value.slice(0, 10);
}

function buildTweetUrl(response: MichaelSaylorTopLikedTweetResponse | null): string {
  if (response?.top_tweet === null || response === null) {
    return "#";
  }

  return `https://x.com/${response.subject.username}/status/${response.top_tweet.platform_tweet_id}`;
}

function renderActionIcon(icon: "reply" | "repost" | "like" | "bookmark") {
  switch (icon) {
    case "reply":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M20 11.5c0 4.7-4.4 8.5-9.8 8.5-1.2 0-2.4-.2-3.5-.6L2 21l1.7-4C2.7 15.5 2 13.6 2 11.5 2 6.8 6.4 3 11.8 3S20 6.8 20 11.5Z" />
        </svg>
      );
    case "repost":
      return (
        <svg viewBox="0 0 24 24">
          <path d="m6 7 3-3 3 3M9 4v11a2 2 0 0 0 2 2h7m-1 0-3 3-3-3m3 3V9a2 2 0 0 0-2-2H5" />
        </svg>
      );
    case "like":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M12 21s-6.7-4.4-9.2-8.2C.7 9.6 2.1 5.5 6.1 4.6c2-.4 4 .3 5.2 1.9 1.2-1.6 3.2-2.3 5.2-1.9 4 .9 5.4 5 3.3 8.2C18.7 16.6 12 21 12 21Z" />
        </svg>
      );
    case "bookmark":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M6 4.5A1.5 1.5 0 0 1 7.5 3h9A1.5 1.5 0 0 1 18 4.5V21l-6-4-6 4V4.5Z" />
        </svg>
      );
  }
}
