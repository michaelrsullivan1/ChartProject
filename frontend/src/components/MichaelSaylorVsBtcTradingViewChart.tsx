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

type MichaelSaylorVsBtcTradingViewChartProps = {
  payload: MichaelSaylorVsBtcResponse;
};

type HoverSnapshot = {
  dateLabel: string;
  btcPriceLabel: string;
  tweetCountLabel: string;
  hasBtcValue: boolean;
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
  const btcSeriesData = useMemo(() => buildBtcSeries(payload), [payload]);
  const tweetSeriesData = useMemo(() => buildTweetSeries(payload), [payload]);
  const [hoverSnapshot, setHoverSnapshot] = useState<HoverSnapshot>(() =>
    buildLatestHoverSnapshot(btcSeriesData, tweetSeriesData),
  );

  useEffect(() => {
    setHoverSnapshot(buildLatestHoverSnapshot(btcSeriesData, tweetSeriesData));
  }, [btcSeriesData, tweetSeriesData]);

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

    chart.subscribeCrosshairMove(handleCrosshairMove);

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
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [btcSeriesData, tweetSeriesData]);

  return (
    <div className="tradingview-chart-shell">
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

      <div className="tradingview-chart" ref={containerRef} />
    </div>
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

function findTweetPointForTime(time: Time, tweetSeriesData: AreaData<Time>[]): AreaData<Time> | undefined {
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
