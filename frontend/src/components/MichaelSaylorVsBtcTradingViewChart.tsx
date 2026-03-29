import { useEffect, useMemo, useRef, useState } from "react";

import {
  AreaSeries,
  BaselineSeries,
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type AreaData,
  type BaselineData,
  type LineData,
  type MouseEventParams,
  type Time,
  type WhitespaceData,
} from "lightweight-charts";

import {
  fetchAuthorTopLikedTweet,
  type AuthorOverviewResponse,
  type AuthorSentimentResponse,
  type AuthorTopLikedTweetResponse,
} from "../api/authorOverview";
import type { OverviewDefinition } from "../config/overviews";
import {
  buildSentimentDeviationSeries,
  type SentimentMode,
} from "../lib/sentiment";

type MichaelSaylorVsBtcTradingViewChartProps = {
  overview: OverviewDefinition;
  payload: AuthorOverviewResponse;
  sentimentPayload: AuthorSentimentResponse;
  sentimentMode: SentimentMode;
  onSentimentModeChange: (mode: SentimentMode) => void;
};

type HoverSnapshot = {
  dateLabel: string;
  btcPriceLabel: string;
  mstrPriceLabel: string;
  tweetCountLabel: string;
  sentimentLabel: string;
  hasBtcValue: boolean;
  hasMstrValue: boolean;
};

type TopTweetPanelState = {
  status: "idle" | "waiting" | "loading" | "loaded" | "error";
  weekStart: string | null;
  response: AuthorTopLikedTweetResponse | null;
  error: string | null;
};

type SelectedWeek = {
  weekStart: string;
};

type PriceMode = "btc" | "mstr" | "both";
type ActivityMode = "tweets" | "likes" | "bookmarks" | "impressions";
type SentimentSeriesPoint = BaselineData<Time> | WhitespaceData<Time>;

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

const sentimentRangeFocusStart = new Date("2020-08-01T00:00:00Z").getTime();

const chartOptions = {
  layout: {
    background: {
      type: ColorType.Solid,
      color: "rgba(12, 10, 8, 0)",
    },
    textColor: "#d4c5ad",
    attributionLogo: false,
    panes: {
      enableResize: true,
      separatorColor: "rgba(255, 245, 220, 0.16)",
      separatorHoverColor: "rgba(255, 178, 64, 0.2)",
    },
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
    axisPressedMouseMove: {
      time: true,
      price: false,
    },
    mouseWheel: true,
    pinch: true,
  },
};

export function MichaelSaylorVsBtcTradingViewChart({
  overview,
  payload,
  sentimentPayload,
  sentimentMode,
  onSentimentModeChange,
}: MichaelSaylorVsBtcTradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const topTweetCacheRef = useRef(new Map<string, AuthorTopLikedTweetResponse>());
  const [priceMode, setPriceMode] = useState<PriceMode>("btc");
  const [activityMode, setActivityMode] = useState<ActivityMode>("tweets");
  const [showWatermark, setShowWatermark] = useState(true);
  const btcSeriesData = useMemo(() => buildBtcSeries(payload), [payload]);
  const mstrSeriesData = useMemo(() => buildMstrSeries(payload), [payload]);
  const activitySeriesData = useMemo(() => buildActivitySeries(payload, activityMode), [payload, activityMode]);
  const activityRange = useMemo(
    () => buildActivityRange(activitySeriesData, activityMode),
    [activitySeriesData, activityMode],
  );
  const sentimentSeriesData = useMemo<SentimentSeriesPoint[]>(
    () =>
      buildSentimentDeviationSeries(sentimentPayload, sentimentMode).map((point) => {
        const time = toBusinessDay(point.periodStart);
        if (point.value === null) {
          return { time };
        }

        return {
          time,
          value: point.value,
        };
      }),
    [sentimentPayload, sentimentMode],
  );
  const sentimentRange = useMemo(
    () => buildSymmetricSentimentRange(sentimentSeriesData, sentimentMode),
    [sentimentSeriesData, sentimentMode],
  );
  const [hoverSnapshot, setHoverSnapshot] = useState<HoverSnapshot>(() =>
    buildLatestHoverSnapshot(
      btcSeriesData,
      mstrSeriesData,
      activitySeriesData,
      sentimentSeriesData,
      activityMode,
    ),
  );
  const [selectedWeek, setSelectedWeek] = useState<SelectedWeek | null>(null);
  const [topTweetPanel, setTopTweetPanel] = useState<TopTweetPanelState>({
    status: "idle",
    weekStart: null,
    response: null,
    error: null,
  });
  const activityVisuals = useMemo(() => getActivityVisuals(activityMode), [activityMode]);

  useEffect(() => {
    setHoverSnapshot(
      buildLatestHoverSnapshot(
        btcSeriesData,
        mstrSeriesData,
        activitySeriesData,
        sentimentSeriesData,
        activityMode,
      ),
    );
  }, [btcSeriesData, mstrSeriesData, activitySeriesData, sentimentSeriesData, activityMode]);

  useEffect(() => {
    if (selectedWeek === null) {
      return;
    }

    const activeWeek = selectedWeek;

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
        const response = await fetchAuthorTopLikedTweet(
          overview.apiBasePath,
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
  }, [overview.apiBasePath, selectedWeek]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }

    const chart = createChart(container, {
      ...chartOptions,
      width: container.clientWidth,
      height: container.clientHeight,
      leftPriceScale: {
        visible: priceMode === "mstr" || priceMode === "both",
        borderVisible: false,
      },
      rightPriceScale: {
        visible: priceMode === "btc" || priceMode === "both",
        borderVisible: false,
      },
    });

    const btcSeries = chart.addSeries(LineSeries, {
      title: "",
      color: "#ffb240",
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 5,
      crosshairMarkerBorderWidth: 2,
      crosshairMarkerBorderColor: "#ffb240",
      crosshairMarkerBackgroundColor: "#17130f",
      lastValueVisible: false,
      priceLineVisible: false,
      priceLineColor: "#ffb240",
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });
    const mstrSeries = chart.addSeries(LineSeries, {
      title: "",
      color: "#ff6c8b",
      lineWidth: 2,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 5,
      crosshairMarkerBorderWidth: 2,
      crosshairMarkerBorderColor: "#ff6c8b",
      crosshairMarkerBackgroundColor: "#17130f",
      lastValueVisible: false,
      priceLineVisible: false,
      priceLineColor: "#ff6c8b",
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
      priceScaleId: "left",
    });

    const activitySeries = chart.addSeries(
      AreaSeries,
      {
        title: "",
        lineColor: activityVisuals.lineColor,
        topColor: activityVisuals.topColor,
        bottomColor: activityVisuals.bottomColor,
        lineWidth: 3,
        lineType: LineType.Curved,
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        priceFormat: {
          type: "volume",
        },
        autoscaleInfoProvider: () => ({
          priceRange: activityRange,
        }),
      },
      1,
    );

    const sentimentSeries = chart.addSeries(
      BaselineSeries,
      {
        title: "",
        baseValue: {
          type: "price",
          price: 0,
        },
        topLineColor: "#7af0b6",
        topFillColor1: "rgba(122, 240, 182, 0.26)",
        topFillColor2: "rgba(122, 240, 182, 0.04)",
        bottomLineColor: "#ff6c6c",
        bottomFillColor1: "rgba(255, 108, 108, 0.24)",
        bottomFillColor2: "rgba(255, 108, 108, 0.04)",
        lineWidth: 3,
        lineType: LineType.Curved,
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        priceFormat: {
          type: "custom",
          minMove: 0.001,
          formatter: formatSignedSentimentPercent,
        },
        autoscaleInfoProvider: () => ({
          priceRange: sentimentRange,
        }),
      },
      2,
    );

    chart.priceScale("right", 0).applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.08,
      },
    });
    chart.priceScale("left", 0).applyOptions({
      visible: priceMode === "mstr" || priceMode === "both",
      borderVisible: false,
      scaleMargins: {
        top: 0.12,
        bottom: 0.08,
      },
    });
    chart.priceScale("right", 0).applyOptions({
      visible: priceMode === "btc" || priceMode === "both",
      borderVisible: false,
    });

    chart.priceScale("right", 1).applyOptions({
      scaleMargins: {
        top: 0.16,
        bottom: 0,
      },
    });

    chart.priceScale("right", 2).applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.12,
      },
    });

    btcSeries.setData(priceMode === "mstr" ? [] : btcSeriesData);
    mstrSeries.setData(priceMode === "btc" ? [] : mstrSeriesData);
    activitySeries.setData(activitySeriesData);
    sentimentSeries.setData(sentimentSeriesData);

    const panes = chart.panes();
    panes[0]?.setHeight(300);
    panes[1]?.setHeight(165);
    panes[2]?.setHeight(165);

    chart.timeScale().fitContent();

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        setHoverSnapshot(
          buildLatestHoverSnapshot(
            btcSeriesData,
            mstrSeriesData,
            activitySeriesData,
            sentimentSeriesData,
            activityMode,
          ),
        );
        return;
      }

      const btcPoint = param.seriesData.get(btcSeries) as LineData<Time> | undefined;
      const mstrPoint = param.seriesData.get(mstrSeries) as LineData<Time> | undefined;
      const activityPoint = findWeeklyPointForTime(param.time, activitySeriesData);
      const sentimentPoint = findWeeklyPointForTime(param.time, sentimentSeriesData);

      setHoverSnapshot({
        dateLabel: formatTimeLabel(param.time),
        btcPriceLabel:
          btcPoint?.value !== undefined ? currencyFormatter.format(btcPoint.value) : "No BTC data",
        mstrPriceLabel:
          mstrPoint?.value !== undefined
            ? currencyFormatter.format(mstrPoint.value)
            : "No MSTR data",
        tweetCountLabel:
          activityPoint?.value !== undefined
            ? formatActivityHoverValue(activityMode, activityPoint.value)
            : `No ${activityMode} bucket`,
        sentimentLabel: hasSeriesValue(sentimentPoint)
          ? formatSignedSentiment(sentimentPoint.value)
          : "No sentiment bucket",
        hasBtcValue: btcPoint?.value !== undefined,
        hasMstrValue: mstrPoint?.value !== undefined,
      });
    };

    const handleClick = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        return;
      }

      const activityPoint = findWeeklyPointForTime(param.time, activitySeriesData);
      if (!activityPoint || typeof activityPoint.time !== "string") {
        return;
      }

      const weekStart = activityPoint.time;

      setSelectedWeek({
        weekStart,
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
  }, [
    btcSeriesData,
    mstrSeriesData,
    activitySeriesData,
    activityRange,
    sentimentSeriesData,
    sentimentRange,
    activityMode,
    priceMode,
  ]);

  return (
    <div className="tradingview-chart-shell">
      <aside className="chart-sidebar chart-sidebar-left">
        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Top Pane</p>
          <div className="chart-toggle-group chart-toggle-group-compact" role="group" aria-label="Top pane asset">
            {(
              [
                ["btc", "BTC"],
                ["mstr", "MSTR"],
                ["both", "Both"],
              ] as const
            ).map(([mode, label]) => (
              <button
                key={mode}
                className={`chart-toggle-button${priceMode === mode ? " is-active" : ""}`}
                onClick={() => setPriceMode(mode)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Middle Pane</p>
          <div className="chart-toggle-group" role="group" aria-label="Middle pane metric">
            {(
              [
                ["tweets", "Tweets / week"],
                ["likes", "Likes / week"],
                ["bookmarks", "Bookmarks / week"],
                ["impressions", "Impressions / week"],
              ] as const
            ).map(([mode, label]) => (
              <button
                key={mode}
                className={`chart-toggle-button${activityMode === mode ? " is-active" : ""}`}
                onClick={() => setActivityMode(mode)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Sentiment Mode</p>
          <div className="chart-toggle-group" role="group" aria-label="Sentiment smoothing mode">
            {(
              [
                ["weighted-4w", "4W weighted"],
                ["weighted-8w", "8W weighted"],
                ["weighted-12w", "12W weighted"],
                ["raw", "Raw"],
              ] as const
            ).map(([mode, label]) => (
              <button
                key={mode}
                className={`chart-toggle-button${sentimentMode === mode ? " is-active" : ""}`}
                onClick={() => onSentimentModeChange(mode)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
          <p className="chart-control-note">
            Smoothed modes use trailing weekly averages weighted by scored tweet count, so
            low-volume weeks carry less influence.
          </p>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Watermark</p>
          <div className="chart-toggle-group chart-toggle-group-compact" role="group" aria-label="Chart watermark visibility">
            <button
              className={`chart-toggle-button${showWatermark ? " is-active" : ""}`}
              onClick={() => setShowWatermark(true)}
              type="button"
            >
              On
            </button>
            <button
              className={`chart-toggle-button${showWatermark ? "" : " is-active"}`}
              onClick={() => setShowWatermark(false)}
              type="button"
            >
              Off
            </button>
          </div>
        </div>
      </aside>

      <div className="chart-stage">
        {showWatermark ? (
          <div aria-hidden="true" className="chart-watermark">
            <span className="chart-watermark-name">Michael Sullivan</span>
            <span className="chart-watermark-handle">@SullyMichaelvan</span>
          </div>
        ) : null}
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
            <span className="chart-hover-label">MSTR</span>
            <span
              className={`chart-hover-value${hoverSnapshot.hasMstrValue ? "" : " is-muted"}`}
            >
              {hoverSnapshot.mstrPriceLabel}
            </span>
          </div>
          <div className="chart-hover-item">
            <span className="chart-hover-label">{activityHoverLabel(activityMode)}</span>
            <span className="chart-hover-value">{hoverSnapshot.tweetCountLabel}</span>
          </div>
          <div className="chart-hover-item">
            <span className="chart-hover-label">Sentiment Deviation</span>
            <span className="chart-hover-value">{hoverSnapshot.sentimentLabel}</span>
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

      {topTweetPanel.status === "loaded" && topTweet === null ? (
        <p className="top-tweet-status">No top liked tweet was found for this selected week.</p>
      ) : null}

      {topTweet !== null ? (
        <>
          <div className="tweet-preview-card">
            <div className="tweet-preview-header">
              <div className="tweet-preview-identity">
                {topTweetPanel.response?.subject.profile_image_url ? (
                  <img
                    alt={topTweetPanel.response.subject.display_name ?? topTweetPanel.response.subject.username}
                    className="tweet-preview-avatar"
                    src={topTweetPanel.response.subject.profile_image_url}
                  />
                ) : (
                  <div className="tweet-preview-avatar tweet-preview-avatar-fallback" aria-hidden="true">
                    {buildAvatarInitials(topTweetPanel.response?.subject)}
                  </div>
                )}

                <div className="tweet-preview-author-block">
                  <p className="tweet-preview-name">
                    {topTweetPanel.response?.subject.display_name ??
                      topTweetPanel.response?.subject.username ??
                      "Unknown author"}
                  </p>
                  <p className="tweet-preview-handle">
                    @{topTweetPanel.response?.subject.username ?? "unknown"}
                  </p>
                </div>
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
      className={`tweet-action-stat tweet-action-stat-${icon}${tone === "accent" ? " is-accent" : ""}`}
      title={label}
    >
      <span className="tweet-action-icon" aria-hidden="true">
        {renderActionIcon(icon)}
      </span>
      <span>{formatCompactCount(value ?? 0)}</span>
    </span>
  );
}

function buildBtcSeries(payload: AuthorOverviewResponse): LineData<Time>[] {
  return payload.btc_series.map((point) => ({
    time: toBusinessDay(point.timestamp),
    value: point.price_usd,
  }));
}

function buildMstrSeries(payload: AuthorOverviewResponse): LineData<Time>[] {
  return payload.mstr_series.map((point) => ({
    time: toBusinessDay(point.timestamp),
    value: point.price_usd,
  }));
}

function buildActivitySeries(
  payload: AuthorOverviewResponse,
  activityMode: ActivityMode,
): AreaData<Time>[] {
  return payload.tweet_series.map((point) => ({
    time: toBusinessDay(point.period_start),
    value: activityValueForMode(point, activityMode),
  }));
}

function buildLatestHoverSnapshot(
  btcSeriesData: LineData<Time>[],
  mstrSeriesData: LineData<Time>[],
  activitySeriesData: AreaData<Time>[],
  sentimentSeriesData: SentimentSeriesPoint[],
  activityMode: ActivityMode,
): HoverSnapshot {
  const latestBtc = btcSeriesData[btcSeriesData.length - 1];
  const latestMstr = mstrSeriesData[mstrSeriesData.length - 1];
  const latestActivity = activitySeriesData[activitySeriesData.length - 1];
  const latestSentiment = sentimentSeriesData[sentimentSeriesData.length - 1];
  const time =
    latestBtc?.time ?? latestMstr?.time ?? latestActivity?.time ?? latestSentiment?.time ?? "1970-01-01";

  return {
    dateLabel: formatTimeLabel(time),
    btcPriceLabel:
      latestBtc?.value !== undefined ? currencyFormatter.format(latestBtc.value) : "No BTC data",
    mstrPriceLabel:
      latestMstr?.value !== undefined ? currencyFormatter.format(latestMstr.value) : "No MSTR data",
    tweetCountLabel:
      latestActivity?.value !== undefined
        ? formatActivityHoverValue(activityMode, latestActivity.value)
        : `No ${activityMode} bucket`,
    sentimentLabel:
      hasSeriesValue(latestSentiment)
        ? formatSignedSentiment(latestSentiment.value)
        : "No sentiment bucket",
    hasBtcValue: latestBtc?.value !== undefined,
    hasMstrValue: latestMstr?.value !== undefined,
  };
}

function findWeeklyPointForTime<T extends { time: Time; value?: number }>(
  time: Time,
  seriesData: T[],
): T | undefined {
  const hoveredDate = normalizeTime(time).getTime();

  for (let index = seriesData.length - 1; index >= 0; index -= 1) {
    const point = seriesData[index];
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

function formatSignedSentiment(value: number): string {
  return formatSignedSentimentPercent(value);
}

function formatSignedSentimentPercent(value: number): string {
  const percentage = value * 100;
  const formatted = percentage.toFixed(1);
  return percentage > 0 ? `+${formatted}%` : `${formatted}%`;
}

function activityModeLabel(mode: ActivityMode): string {
  switch (mode) {
    case "tweets":
      return "Tweets / week";
    case "likes":
      return "Likes / week";
    case "bookmarks":
      return "Bookmarks / week";
    case "impressions":
      return "Impressions / week";
  }
}

function activityHoverLabel(mode: ActivityMode): string {
  switch (mode) {
    case "tweets":
      return "Tweets That Week";
    case "likes":
      return "Likes That Week";
    case "bookmarks":
      return "Bookmarks That Week";
    case "impressions":
      return "Impressions That Week";
  }
}

function formatActivityHoverValue(mode: ActivityMode, value: number): string {
  switch (mode) {
    case "tweets":
      return `${integerFormatter.format(value)} tweets`;
    case "likes":
      return `${integerFormatter.format(value)} likes`;
    case "bookmarks":
      return `${integerFormatter.format(value)} bookmarks`;
    case "impressions":
      return `${formatCompactCount(value)} impressions`;
  }
}

function activityValueForMode(
  point: AuthorOverviewResponse["tweet_series"][number],
  mode: ActivityMode,
): number {
  switch (mode) {
    case "tweets":
      return point.tweet_count;
    case "likes":
      return point.like_count;
    case "bookmarks":
      return point.bookmark_count;
    case "impressions":
      return point.impression_count;
  }
}

function getActivityVisuals(mode: ActivityMode): {
  lineColor: string;
  topColor: string;
  bottomColor: string;
  markerBorderColor: string;
} {
  switch (mode) {
    case "tweets":
      return {
        lineColor: "#76c7ff",
        topColor: "rgba(118, 199, 255, 0.22)",
        bottomColor: "rgba(118, 199, 255, 0.02)",
        markerBorderColor: "#76c7ff",
      };
    case "likes":
      return {
        lineColor: "#ff6c8b",
        topColor: "rgba(255, 108, 139, 0.22)",
        bottomColor: "rgba(255, 108, 139, 0.03)",
        markerBorderColor: "#ff6c8b",
      };
    case "bookmarks":
      return {
        lineColor: "#d5a6ff",
        topColor: "rgba(213, 166, 255, 0.22)",
        bottomColor: "rgba(213, 166, 255, 0.03)",
        markerBorderColor: "#d5a6ff",
      };
    case "impressions":
      return {
        lineColor: "#4fe0c6",
        topColor: "rgba(79, 224, 198, 0.22)",
        bottomColor: "rgba(79, 224, 198, 0.03)",
        markerBorderColor: "#4fe0c6",
      };
  }
}

function buildActivityRange(
  points: AreaData<Time>[],
  mode: ActivityMode,
): { minValue: number; maxValue: number } {
  const focusedValues: number[] = [];
  const fullValues: number[] = [];

  for (const point of points) {
    const value = point.value;
    if (typeof value !== "number") {
      continue;
    }

    fullValues.push(value);
    if (normalizeTime(point.time).getTime() >= sentimentRangeFocusStart) {
      focusedValues.push(value);
    }
  }

  const sourceValues = focusedValues.length > 0 ? focusedValues : fullValues;
  const percentile =
    mode === "impressions"
      ? 0.985
      : mode === "likes" || mode === "bookmarks"
        ? 0.99
        : 0.995;
  const paddingMultiplier =
    mode === "impressions"
      ? 1.06
      : mode === "likes" || mode === "bookmarks"
        ? 1.08
        : 1.1;
  const minimumRange =
    mode === "impressions"
      ? 1_000
      : mode === "likes"
        ? 100
        : mode === "bookmarks"
          ? 25
          : 5;
  const maxValue = Math.max(quantile(sourceValues, percentile) * paddingMultiplier, minimumRange);

  return {
    minValue: 0,
    maxValue,
  };
}

function buildSymmetricSentimentRange(
  points: SentimentSeriesPoint[],
  sentimentMode: SentimentMode,
): { minValue: number; maxValue: number } {
  const focusedAbsoluteValues: number[] = [];
  const fullAbsoluteValues: number[] = [];

  for (const point of points) {
    if (!hasSeriesValue(point)) {
      continue;
    }

    const absoluteValue = Math.abs(point.value);
    fullAbsoluteValues.push(absoluteValue);

    if (normalizeTime(point.time).getTime() >= sentimentRangeFocusStart) {
      focusedAbsoluteValues.push(absoluteValue);
    }
  }

  const sourceValues = focusedAbsoluteValues.length > 0 ? focusedAbsoluteValues : fullAbsoluteValues;
  const percentile =
    sentimentMode === "raw"
      ? 0.98
      : sentimentMode === "weighted-4w"
        ? 0.99
        : sentimentMode === "weighted-8w"
          ? 0.975
          : 0.95;
  const paddingMultiplier =
    sentimentMode === "raw"
      ? 1.1
      : sentimentMode === "weighted-4w"
        ? 1.08
        : sentimentMode === "weighted-8w"
          ? 1.06
          : 1.04;
  const minimumRange =
    sentimentMode === "raw"
      ? 0.05
      : sentimentMode === "weighted-4w"
        ? 0.04
        : sentimentMode === "weighted-8w"
          ? 0.035
          : 0.03;
  const referenceValue = quantile(sourceValues, percentile);
  const paddedMax = Math.max(referenceValue * paddingMultiplier, minimumRange);

  return {
    minValue: -paddedMax,
    maxValue: paddedMax,
  };
}

function quantile(values: number[], percentile: number): number {
  if (values.length === 0) {
    return 0;
  }

  const sortedValues = [...values].sort((left, right) => left - right);
  const position = Math.min(sortedValues.length - 1, Math.max(0, Math.floor(percentile * (sortedValues.length - 1))));

  return sortedValues[position] ?? 0;
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

function hasSeriesValue(point: unknown): point is { value: number } {
  return (
    typeof point === "object" &&
    point !== null &&
    "value" in point &&
    typeof (point as { value?: unknown }).value === "number"
  );
}

function buildTweetUrl(response: AuthorTopLikedTweetResponse | null): string {
  if (response?.top_tweet === null || response === null) {
    return "#";
  }

  return `https://x.com/${response.subject.username}/status/${response.top_tweet.platform_tweet_id}`;
}

function buildAvatarInitials(
  subject: AuthorTopLikedTweetResponse["subject"] | undefined,
): string {
  const source = subject?.display_name ?? subject?.username ?? "";
  const parts = source
    .split(/\s+/)
    .map((part) => part.trim())
    .filter(Boolean);

  if (parts.length === 0) {
    return "?";
  }

  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }

  return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
}

function renderActionIcon(icon: "reply" | "repost" | "like" | "bookmark") {
  switch (icon) {
    case "reply":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M21 12c0 4.4-4 8-9 8-1 0-2-.1-2.9-.4L4 21l1.5-4A7.5 7.5 0 0 1 3 12c0-4.4 4-8 9-8s9 3.6 9 8Z" />
        </svg>
      );
    case "repost":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M17 4 21 8l-4 4" />
          <path d="M3 11V9a1 1 0 0 1 1-1h17" />
          <path d="M7 20 3 16l4-4" />
          <path d="M21 13v2a1 1 0 0 1-1 1H3" />
        </svg>
      );
    case "like":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M12 20.3s-7-4.4-9.3-8.3C.9 8.9 2.2 5.5 5.7 4.7c2-.4 4 .4 5.3 2 1.3-1.6 3.3-2.4 5.3-2 3.5.8 4.8 4.2 3 7.3-2.3 3.9-9.3 8.3-9.3 8.3Z" />
        </svg>
      );
    case "bookmark":
      return (
        <svg viewBox="0 0 24 24">
          <path d="M6 3.5h12a1 1 0 0 1 1 1V21l-7-4-7 4V4.5a1 1 0 0 1 1-1Z" />
        </svg>
      );
  }
}
