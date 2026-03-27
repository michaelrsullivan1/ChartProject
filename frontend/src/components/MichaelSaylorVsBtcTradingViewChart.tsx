import { useEffect, useRef } from "react";

import {
  ColorType,
  HistogramSeries,
  LineSeries,
  createChart,
  type HistogramData,
  type LineData,
  type Time,
} from "lightweight-charts";

import type { MichaelSaylorVsBtcResponse } from "../api/michaelSaylorVsBtc";

type MichaelSaylorVsBtcTradingViewChartProps = {
  payload: MichaelSaylorVsBtcResponse;
};

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
    barSpacing: 8,
    minBarSpacing: 0.4,
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
      HistogramSeries,
      {
        title: "Tweets / week",
        color: "#ffb240",
        lastValueVisible: false,
        priceLineVisible: false,
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

    btcSeries.setData(buildBtcSeries(payload));
    tweetSeries.setData(buildTweetSeries(payload));

    const panes = chart.panes();
    panes[0]?.setHeight(320);
    panes[1]?.setHeight(160);

    chart.timeScale().fitContent();

    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) {
        return;
      }

      chart.resize(entry.contentRect.width, entry.contentRect.height);
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
    };
  }, [payload]);

  return <div className="tradingview-chart" ref={containerRef} />;
}

function buildBtcSeries(payload: MichaelSaylorVsBtcResponse): LineData<Time>[] {
  return payload.btc_series.map((point) => ({
    time: toBusinessDay(point.timestamp),
    value: point.price_usd,
  }));
}

function buildTweetSeries(payload: MichaelSaylorVsBtcResponse): HistogramData<Time>[] {
  return payload.tweet_series.map((point) => ({
    time: toBusinessDay(point.period_start),
    value: point.tweet_count,
    color: point.tweet_count === 0 ? "rgba(255, 178, 64, 0.18)" : "#ffb240",
  }));
}

function toBusinessDay(value: string): string {
  return value.slice(0, 10);
}
