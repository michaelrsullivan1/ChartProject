import { useEffect, useMemo, useRef, useState } from "react";

import {
  ColorType,
  HistogramSeries,
  LineSeries,
  LineType,
  createChart,
  isBusinessDay,
  type HistogramData,
  type LineData,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import type { AuthorBitcoinMentionsResponse, BitcoinMention } from "../api/bitcoinMentions";
import { TweetPreviewCard } from "./TweetPreviewCard";

type BitcoinMentionsHistoryChartProps = {
  hoverSnapshot: HoverSnapshot | null;
  payload: AuthorBitcoinMentionsResponse;
  onHoverSnapshotChange: (snapshot: HoverSnapshot) => void;
};

export type HoverSnapshot = {
  dateLabel: string;
  btcPriceLabel: string;
};

const currencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 2,
});

const integerFormatter = new Intl.NumberFormat("en-US");

const dateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
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
    panes: {
      enableResize: true,
      separatorColor: "rgba(255, 245, 220, 0.12)",
      separatorHoverColor: "rgba(255, 178, 64, 0.18)",
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
    barSpacing: 7.5,
    minBarSpacing: 0.2,
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

export function BitcoinMentionsHistoryChart({
  hoverSnapshot,
  payload,
  onHoverSnapshotChange,
}: BitcoinMentionsHistoryChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const plottedMentions = useMemo(() => buildPlottedMentions(payload.mentions), [payload.mentions]);
  const mentionWindow = useMemo(() => {
    const firstMentionAt = payload.summary.first_mention_at;
    const latestMentionAt = payload.summary.latest_mention_at;
    if (!firstMentionAt || !latestMentionAt) {
      return null;
    }

    return {
      startTimestamp: toDayStartUnixSeconds(firstMentionAt),
      endTimestamp: toDayStartUnixSeconds(latestMentionAt),
    };
  }, [payload.summary.first_mention_at, payload.summary.latest_mention_at]);
  const mentionsByPlotTimestamp = useMemo(
    () => new Map(plottedMentions.map((item) => [item.plotTimestamp, item.mention])),
    [plottedMentions],
  );
  const btcSeriesData = useMemo<LineData<Time>[]>(
    () =>
      payload.btc_series
        .filter((point) => {
          if (!mentionWindow) {
            return true;
          }

          const timestamp = toUnixSeconds(point.timestamp);
          return (
            timestamp >= mentionWindow.startTimestamp &&
            timestamp <= mentionWindow.endTimestamp
          );
        })
        .map((point) => ({
          time: toChartTimestamp(point.timestamp),
          value: point.price_usd,
        })),
    [mentionWindow, payload.btc_series],
  );
  const mentionDotsData = useMemo<LineData<Time>[]>(
    () =>
      plottedMentions.map((item) => ({
        time: item.plotTimestamp as UTCTimestamp,
        value: item.mention.btc_price_usd,
      })),
    [plottedMentions],
  );
  const mentionVolumeData = useMemo<HistogramData<Time>[]>(
    () => buildMentionVolumeSeries(payload, mentionWindow),
    [mentionWindow, payload],
  );
  const mentionVolumeRange = useMemo(() => {
    const maxValue = mentionVolumeData.reduce(
      (currentMax, point) => Math.max(currentMax, point.value),
      0,
    );
    return {
      minValue: 0,
      maxValue: Math.max(1, Math.ceil(maxValue * 1.2)),
    };
  }, [mentionVolumeData]);
  const [selectedMention, setSelectedMention] = useState<BitcoinMention | null>(
    payload.summary.best_timed_mention,
  );

  useEffect(() => {
    const nextSnapshot = buildLatestHoverSnapshot(payload);
    onHoverSnapshotChange(nextSnapshot);
    setSelectedMention(payload.summary.best_timed_mention);
  }, [onHoverSnapshotChange, payload]);

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
      color: "#ffb240",
      lineWidth: 2,
      lineType: LineType.Curved,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 5,
      crosshairMarkerBorderWidth: 2,
      crosshairMarkerBorderColor: "#ffb240",
      crosshairMarkerBackgroundColor: "#17130f",
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    const mentionSeries = chart.addSeries(LineSeries, {
      color: "rgba(0, 0, 0, 0)",
      lineWidth: 1,
      pointMarkersVisible: true,
      pointMarkersRadius: 4,
      crosshairMarkerVisible: false,
      lastValueVisible: false,
      priceLineVisible: false,
      priceFormat: {
        type: "price",
        precision: 2,
        minMove: 0.01,
      },
    });

    const volumeSeries = chart.addSeries(
      HistogramSeries,
      {
        color: "rgba(118, 199, 255, 0.62)",
        base: 0,
        lastValueVisible: false,
        priceLineVisible: false,
        priceFormat: {
          type: "custom",
          minMove: 1,
          formatter: (value: number) => integerFormatter.format(Math.round(value)),
        },
        autoscaleInfoProvider: () => ({
          priceRange: mentionVolumeRange,
        }),
      },
      1,
    );

    btcSeries.setData(btcSeriesData);
    mentionSeries.setData(mentionDotsData);
    volumeSeries.setData(mentionVolumeData);

    chart.priceScale("right", 0).applyOptions({
      borderVisible: false,
      scaleMargins: {
        top: 0.08,
        bottom: 0.06,
      },
    });
    chart.priceScale("right", 1).applyOptions({
      borderVisible: false,
      scaleMargins: {
        top: 0.12,
        bottom: 0.16,
      },
    });

    const panes = chart.panes();
    panes[0]?.setHeight(410);
    panes[1]?.setHeight(130);

    chart.timeScale().fitContent();

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.time) {
        const nextSnapshot = buildLatestHoverSnapshot(payload);
        onHoverSnapshotChange(nextSnapshot);
        return;
      }

      const dayTimestamp = normalizeChartTimeToDayTimestamp(param.time);
      const btcPoint = param.seriesData.get(btcSeries) as LineData<Time> | undefined;
      const nextSnapshot = {
        dateLabel: formatChartTime(param.time),
        btcPriceLabel:
          btcPoint?.value !== undefined
            ? currencyFormatter.format(btcPoint.value)
            : currencyFormatter.format(findClosestBtcPrice(payload, dayTimestamp) ?? 0),
      };
      onHoverSnapshotChange(nextSnapshot);
    };

    const handleClick = (param: MouseEventParams<Time>) => {
      if (!param.time) {
        return;
      }

      const mentionPoint = param.seriesData.get(mentionSeries) as LineData<Time> | undefined;
      if (mentionPoint?.value !== undefined) {
        const directMatch = mentionsByPlotTimestamp.get(normalizeChartTimeToExactTimestamp(param.time));
        if (directMatch) {
          setSelectedMention(directMatch);
          return;
        }
      }

      const nearestMention = findNearestMention(
        plottedMentions,
        normalizeChartTimeToExactTimestamp(param.time),
      );
      if (nearestMention) {
        setSelectedMention(nearestMention);
      }
    };

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });

    chart.subscribeCrosshairMove(handleCrosshairMove);
    chart.subscribeClick(handleClick);
    resizeObserver.observe(container);

    return () => {
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.unsubscribeClick(handleClick);
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [
    btcSeriesData,
    mentionDotsData,
    mentionVolumeData,
    mentionVolumeRange,
    mentionsByPlotTimestamp,
    onHoverSnapshotChange,
    payload,
    plottedMentions,
  ]);

  return (
    <div className="bitcoin-history-layout">
      <div className="chart-stage">
        <div className="tradingview-chart bitcoin-history-chart" ref={containerRef} />
      </div>

      <div className="bitcoin-history-column bitcoin-history-selected-column">
        <article className="top-tweet-card bitcoin-selected-mention-card">
          <p className="top-tweet-eyebrow">Selected Mention</p>
          {selectedMention ? (
            <TweetPreviewCard
              author={payload.subject}
              extraStats={[
                {
                  label: "BTC",
                  value: currencyFormatter.format(selectedMention.btc_price_usd),
                },
                {
                  label: "Return",
                  tone: "accent",
                  value: formatSignedPercent(selectedMention.price_change_since_tweet_pct),
                },
              ]}
              tweet={selectedMention}
            />
          ) : (
            <p className="top-tweet-status">No matching mention is available for this selection.</p>
          )}
        </article>

        <article className="metric-card bitcoin-hover-btc-card">
          <p className="metric-label">BTC Price</p>
          <p className="metric-value">{hoverSnapshot?.btcPriceLabel ?? "N/A"}</p>
          <p className="metric-note">{hoverSnapshot?.dateLabel ?? "No BTC data"}</p>
        </article>
      </div>

      <article className="top-tweet-card bitcoin-selected-mention-card bitcoin-cheapest-entries-card bitcoin-history-column">
        <div className="bitcoin-mentions-panel-header">
          <div>
            <p className="top-tweet-eyebrow">Cheapest Entries</p>
            <h2 className="bitcoin-sidebar-title">Lowest-price Bitcoin mentions</h2>
          </div>
        </div>
        {payload.cheapest_mentions.length > 0 ? (
          <div className="bitcoin-mini-list bitcoin-mini-list-sidebar">
            {payload.cheapest_mentions.map((mention) => (
              <TweetPreviewCard
                key={mention.platform_tweet_id}
                author={payload.subject}
                className="bitcoin-mini-card"
                extraStats={[
                  {
                    label: "BTC",
                    value: currencyFormatter.format(mention.btc_price_usd),
                  },
                  {
                    label: "Return",
                    tone: "accent",
                    value: formatSignedPercent(mention.price_change_since_tweet_pct),
                  },
                ]}
                tweet={mention}
              />
            ))}
          </div>
        ) : (
          <p className="top-tweet-status">No Bitcoin mentions were found for this author.</p>
        )}
      </article>
    </div>
  );
}

function buildLatestHoverSnapshot(payload: AuthorBitcoinMentionsResponse): HoverSnapshot {
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  return {
    dateLabel: latestBtcPoint ? dateFormatter.format(new Date(latestBtcPoint.timestamp)) : "No BTC data",
    btcPriceLabel: latestBtcPoint ? currencyFormatter.format(latestBtcPoint.price_usd) : "No BTC data",
  };
}

function findClosestBtcPrice(
  payload: AuthorBitcoinMentionsResponse,
  targetTimestamp: number,
): number | null {
  let closestPrice: number | null = null;
  let smallestDistance = Number.POSITIVE_INFINITY;
  for (const point of payload.btc_series) {
    const timestamp = toUnixSeconds(point.timestamp);
    const distance = Math.abs(timestamp - targetTimestamp);
    if (distance < smallestDistance) {
      smallestDistance = distance;
      closestPrice = point.price_usd;
    }
  }
  return closestPrice;
}

function buildPlottedMentions(
  mentions: BitcoinMention[],
): Array<{ plotTimestamp: number; mention: BitcoinMention }> {
  const sortedMentions = [...mentions].sort((left, right) =>
    left.created_at_platform.localeCompare(right.created_at_platform),
  );

  const plottedMentions: Array<{ plotTimestamp: number; mention: BitcoinMention }> = [];
  let previousPlotTimestamp = Number.NEGATIVE_INFINITY;
  for (const mention of sortedMentions) {
    const originalTimestamp = toUnixSeconds(mention.created_at_platform);
    const plotTimestamp =
      originalTimestamp <= previousPlotTimestamp ? previousPlotTimestamp + 1 : originalTimestamp;
    plottedMentions.push({
      plotTimestamp,
      mention,
    });
    previousPlotTimestamp = plotTimestamp;
  }

  return plottedMentions;
}

function buildMentionVolumeSeries(
  payload: AuthorBitcoinMentionsResponse,
  mentionWindow: { startTimestamp: number; endTimestamp: number } | null,
): HistogramData<Time>[] {
  const countsByPricingDay = new Map<number, number>();

  for (const mention of payload.mentions) {
    const dayTimestamp = toUnixSeconds(mention.pricing_day);
    countsByPricingDay.set(dayTimestamp, (countsByPricingDay.get(dayTimestamp) ?? 0) + 1);
  }

  return payload.btc_series
    .filter((point) => {
      if (!mentionWindow) {
        return true;
      }

      const timestamp = toUnixSeconds(point.timestamp);
      return timestamp >= mentionWindow.startTimestamp && timestamp <= mentionWindow.endTimestamp;
    })
    .map((point) => {
      const dayTimestamp = toUnixSeconds(point.timestamp);
      const mentionCount = countsByPricingDay.get(dayTimestamp) ?? 0;

      return {
        time: toChartTimestamp(point.timestamp),
        value: mentionCount,
        color:
          mentionCount > 0 ? "rgba(118, 199, 255, 0.7)" : "rgba(118, 199, 255, 0.08)",
      };
    });
}

function findNearestMention(
  plottedMentions: Array<{ plotTimestamp: number; mention: BitcoinMention }>,
  targetTimestamp: number,
): BitcoinMention | null {
  let closestMention: BitcoinMention | null = null;
  let smallestDistance = Number.POSITIVE_INFINITY;
  for (const plottedMention of plottedMentions) {
    const distance = Math.abs(plottedMention.plotTimestamp - targetTimestamp);
    if (distance < smallestDistance) {
      smallestDistance = distance;
      closestMention = plottedMention.mention;
    }
  }
  return closestMention;
}

function toChartTimestamp(value: string): UTCTimestamp {
  return toUnixSeconds(value) as UTCTimestamp;
}

function toUnixSeconds(value: string): number {
  return Math.floor(new Date(value).getTime() / 1000);
}

function toDayStartUnixSeconds(value: string): number {
  const date = new Date(value);
  return Math.floor(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()) / 1000);
}

function normalizeChartTimeToDayTimestamp(time: Time): number {
  const exactTimestamp = normalizeChartTimeToExactTimestamp(time);
  return exactTimestamp - (exactTimestamp % 86400);
}

function normalizeChartTimeToExactTimestamp(time: Time): number {
  if (typeof time === "number") {
    return time;
  }
  if (isBusinessDay(time)) {
    return Date.UTC(time.year, time.month - 1, time.day) / 1000;
  }
  return Math.floor(new Date(time).getTime() / 1000);
}

function formatChartTime(time: Time): string {
  if (typeof time === "number") {
    return timestampFormatter.format(new Date(time * 1000));
  }
  if (isBusinessDay(time)) {
    return dateFormatter.format(new Date(Date.UTC(time.year, time.month - 1, time.day)));
  }
  return dateFormatter.format(new Date(time));
}

function formatSignedPercent(value: number): string {
  const prefix = value >= 0 ? "+" : "";
  return `${prefix}${value.toFixed(1)}%`;
}
