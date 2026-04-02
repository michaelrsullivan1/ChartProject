import { useEffect, useMemo, useRef, useState } from "react";

import {
  ColorType,
  LineSeries,
  LineType,
  createChart,
  isBusinessDay,
  type LineData,
  type MouseEventParams,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import type { AuthorBitcoinMentionsResponse, BitcoinMention } from "../api/bitcoinMentions";

type BitcoinMentionsHistoryChartProps = {
  payload: AuthorBitcoinMentionsResponse;
};

type HoverSnapshot = {
  dateLabel: string;
  btcPriceLabel: string;
  mentionsLabel: string;
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

export function BitcoinMentionsHistoryChart({ payload }: BitcoinMentionsHistoryChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const plottedMentions = useMemo(() => buildPlottedMentions(payload.mentions), [payload.mentions]);
  const mentionsByPlotTimestamp = useMemo(
    () => new Map(plottedMentions.map((item) => [item.plotTimestamp, item.mention])),
    [plottedMentions],
  );
  const mentionsByPricingDay = useMemo(() => {
    const map = new Map<number, BitcoinMention[]>();
    for (const mention of payload.mentions) {
      const key = toUnixSeconds(mention.pricing_day);
      const group = map.get(key);
      if (group) {
        group.push(mention);
      } else {
        map.set(key, [mention]);
      }
    }
    return map;
  }, [payload.mentions]);
  const btcSeriesData = useMemo<LineData<Time>[]>(
    () =>
      payload.btc_series.map((point) => ({
        time: toChartTimestamp(point.timestamp),
        value: point.price_usd,
      })),
    [payload.btc_series],
  );
  const mentionDotsData = useMemo<LineData<Time>[]>(
    () =>
      plottedMentions.map((item) => ({
        time: item.plotTimestamp as UTCTimestamp,
        value: item.mention.btc_price_usd,
      })),
    [plottedMentions],
  );
  const [hoverSnapshot, setHoverSnapshot] = useState<HoverSnapshot>(() =>
    buildLatestHoverSnapshot(payload),
  );
  const [selectedMention, setSelectedMention] = useState<BitcoinMention | null>(
    payload.summary.best_timed_mention,
  );

  useEffect(() => {
    setHoverSnapshot(buildLatestHoverSnapshot(payload));
    setSelectedMention(payload.summary.best_timed_mention);
  }, [payload]);

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

    btcSeries.setData(btcSeriesData);
    mentionSeries.setData(mentionDotsData);

    chart.timeScale().fitContent();

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.time) {
        setHoverSnapshot(buildLatestHoverSnapshot(payload));
        return;
      }

      const dayTimestamp = normalizeChartTimeToDayTimestamp(param.time);
      const btcPoint = param.seriesData.get(btcSeries) as LineData<Time> | undefined;
      const mentionPoint = param.seriesData.get(mentionSeries) as LineData<Time> | undefined;
      const mentionsOnDay = mentionsByPricingDay.get(dayTimestamp) ?? [];

      setHoverSnapshot({
        dateLabel: formatChartTime(param.time),
        btcPriceLabel:
          btcPoint?.value !== undefined
            ? currencyFormatter.format(btcPoint.value)
            : currencyFormatter.format(findClosestBtcPrice(payload, dayTimestamp) ?? 0),
        mentionsLabel:
          mentionPoint?.value !== undefined
            ? "1 plotted mention at this timestamp"
            : mentionsOnDay.length > 0
              ? `${integerFormatter.format(mentionsOnDay.length)} mentions on this BTC pricing day`
              : "No plotted mention at this cursor",
      });
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
  }, [btcSeriesData, mentionDotsData, mentionsByPlotTimestamp, mentionsByPricingDay, payload, plottedMentions]);

  return (
    <div className="bitcoin-history-layout">
      <aside className="chart-sidebar chart-sidebar-left">
        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Chart View</p>
          <p className="chart-control-note">
            Full stored BTC history in orange. Each blue dot is one matching tweet plotted at the
            BTC daily close used for the analysis.
          </p>
        </div>

        <div className="chart-hover-strip">
          <div className="chart-hover-item">
            <span className="chart-hover-label">Cursor Date</span>
            <span className="chart-hover-value">{hoverSnapshot.dateLabel}</span>
          </div>
          <div className="chart-hover-item">
            <span className="chart-hover-label">BTC Price</span>
            <span className="chart-hover-value">{hoverSnapshot.btcPriceLabel}</span>
          </div>
          <div className="chart-hover-item">
            <span className="chart-hover-label">Mention Density</span>
            <span className="chart-hover-value">{hoverSnapshot.mentionsLabel}</span>
          </div>
        </div>
      </aside>

      <div className="chart-stage">
        <div className="tradingview-chart bitcoin-history-chart" ref={containerRef} />
      </div>

      <aside className="chart-sidebar">
        <div className="top-tweet-card bitcoin-selected-mention-card">
          <p className="top-tweet-eyebrow">Selected Mention</p>
          {selectedMention ? (
            <>
              <p className="top-tweet-week">{timestampFormatter.format(new Date(selectedMention.created_at_platform))}</p>
              <p className="top-tweet-status">
                BTC at tweet: {currencyFormatter.format(selectedMention.btc_price_usd)}. Value
                today from {currencyFormatter.format(selectedMention.hypothetical_buy_amount_usd)}:{" "}
                {currencyFormatter.format(selectedMention.hypothetical_current_value_usd)}.
              </p>
              <p className="top-tweet-text">{selectedMention.text}</p>
              <div className="tweet-preview-actions">
                <span className="tweet-action-stat is-accent">
                  Likes {integerFormatter.format(selectedMention.like_count ?? 0)}
                </span>
                <span className="tweet-action-stat">
                  Replies {integerFormatter.format(selectedMention.reply_count ?? 0)}
                </span>
                <span className="tweet-action-stat">
                  Reposts {integerFormatter.format(selectedMention.repost_count ?? 0)}
                </span>
                <span className="tweet-action-stat">
                  Return {formatSignedPercent(selectedMention.price_change_since_tweet_pct)}
                </span>
              </div>
              {selectedMention.url ? (
                <a className="bitcoin-selected-mention-link" href={selectedMention.url} rel="noreferrer" target="_blank">
                  Open tweet
                </a>
              ) : null}
            </>
          ) : (
            <p className="top-tweet-status">No plotted mention is available for this selection.</p>
          )}
        </div>
      </aside>
    </div>
  );
}

function buildLatestHoverSnapshot(payload: AuthorBitcoinMentionsResponse): HoverSnapshot {
  const latestBtcPoint = payload.btc_series[payload.btc_series.length - 1];
  return {
    dateLabel: latestBtcPoint ? dateFormatter.format(new Date(latestBtcPoint.timestamp)) : "No BTC data",
    btcPriceLabel: latestBtcPoint ? currencyFormatter.format(latestBtcPoint.price_usd) : "No BTC data",
    mentionsLabel: `${integerFormatter.format(payload.summary.mention_count)} plotted mentions`,
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
