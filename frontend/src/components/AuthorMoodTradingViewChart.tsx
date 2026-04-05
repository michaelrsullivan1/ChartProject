import { useEffect, useMemo, useRef, useState } from "react";

import {
  BaselineSeries,
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type BaselineData,
  type LineData,
  type Time,
  type WhitespaceData,
} from "lightweight-charts";

import type { AuthorMoodResponse, AuthorOverviewResponse } from "../api/authorOverview";
import { buildMoodDeviationSeries } from "../lib/moods";
import type { SentimentMode } from "../lib/sentiment";
import { CHART_WATERMARK_HANDLE } from "../lib/watermark";

type AuthorMoodTradingViewChartProps = {
  payload: AuthorOverviewResponse;
  moodPayload: AuthorMoodResponse;
  selectedMoodLabel: string;
  showWatermark: boolean;
  showMoodSelector?: boolean;
  isScreenshotMode: boolean;
  onScreenshotModeChange: (enabled: boolean) => void;
  sentimentMode: SentimentMode;
  smoothingWeightLabel?: string;
  onSentimentModeChange: (mode: SentimentMode) => void;
  onMoodLabelChange: (label: string) => void;
};

type MoodSeriesPoint = BaselineData<Time> | WhitespaceData<Time>;

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

const moodRangeFocusStart = new Date("2020-08-01T00:00:00Z").getTime();

export function AuthorMoodTradingViewChart({
  payload,
  moodPayload,
  selectedMoodLabel,
  showWatermark,
  showMoodSelector = true,
  isScreenshotMode,
  onScreenshotModeChange,
  sentimentMode,
  smoothingWeightLabel = "scored post count",
  onSentimentModeChange,
  onMoodLabelChange,
}: AuthorMoodTradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const btcSeriesData = useMemo(() => buildBtcSeries(payload), [payload]);
  const moodSeriesData = useMemo<MoodSeriesPoint[]>(
    () =>
      buildMoodDeviationSeries(moodPayload, selectedMoodLabel, sentimentMode).map((point) => {
        const time = toBusinessDay(point.periodStart);
        if (point.value === null) {
          return { time };
        }

        return {
          time,
          value: point.value,
        };
      }),
    [moodPayload, selectedMoodLabel, sentimentMode],
  );
  const moodRange = useMemo(
    () => buildSymmetricMoodRange(moodSeriesData, sentimentMode),
    [moodSeriesData, sentimentMode],
  );

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

    const moodSeries = chart.addSeries(
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
          formatter: formatSignedMoodPercent,
        },
        autoscaleInfoProvider: () => ({
          priceRange: moodRange,
        }),
      },
      1,
    );

    chart.priceScale("right", 0).applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.08,
      },
    });

    chart.priceScale("right", 1).applyOptions({
      scaleMargins: {
        top: 0.12,
        bottom: 0.12,
      },
    });

    btcSeries.setData(btcSeriesData);
    moodSeries.setData(moodSeriesData);

    const panes = chart.panes();
    panes[0]?.setHeight(320);
    panes[1]?.setHeight(190);

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
  }, [btcSeriesData, moodSeriesData, moodRange]);

  return (
    <div className="tradingview-chart-shell">
      <aside className="chart-sidebar chart-sidebar-left">
        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Mood Mode</p>
          <div className="chart-toggle-group" role="group" aria-label="Mood smoothing mode">
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
            Smoothed modes use trailing weekly averages weighted by {smoothingWeightLabel}, so
            lower-coverage weeks carry less influence.
          </p>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Screenshot Mode</p>
          <div className="chart-toggle-group chart-toggle-group-compact" role="group" aria-label="Screenshot mode">
            <button
              className={`chart-toggle-button${isScreenshotMode ? "" : " is-active"}`}
              onClick={() => onScreenshotModeChange(false)}
              type="button"
            >
              Off
            </button>
            <button
              className={`chart-toggle-button${isScreenshotMode ? " is-active" : ""}`}
              onClick={() => onScreenshotModeChange(true)}
              type="button"
            >
              On
            </button>
          </div>
          <p className="chart-control-note">
            Narrows the top metrics to the chart capture width so you can crop out the sidebars.
          </p>
        </div>
      </aside>

      <div className="chart-stage">
        {showWatermark ? (
          <div aria-hidden="true" className="chart-watermark">
            <span className="chart-watermark-handle">{CHART_WATERMARK_HANDLE}</span>
          </div>
        ) : null}
        <div className="tradingview-chart" ref={containerRef} />
      </div>

      {showMoodSelector ? (
        <aside className="chart-sidebar">
          <div className="chart-control-card">
            <p className="chart-control-eyebrow">Mood</p>
            <div className="chart-toggle-group" role="group" aria-label="Mood label">
              {moodPayload.model.mood_labels.map((moodLabel) => (
                <button
                  key={moodLabel}
                  className={`chart-toggle-button${selectedMoodLabel === moodLabel ? " is-active" : ""}`}
                  onClick={() => onMoodLabelChange(moodLabel)}
                  type="button"
                >
                  {formatMoodLabel(moodLabel)}
                </button>
              ))}
            </div>
          </div>
        </aside>
      ) : null}
    </div>
  );
}

function buildBtcSeries(payload: AuthorOverviewResponse): LineData<Time>[] {
  return payload.btc_series.map((point) => ({
    time: toBusinessDay(point.timestamp),
    value: point.price_usd,
  }));
}

function buildSymmetricMoodRange(
  points: MoodSeriesPoint[],
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

    if (normalizeTime(point.time).getTime() >= moodRangeFocusStart) {
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
  const position = Math.min(
    sortedValues.length - 1,
    Math.max(0, Math.floor(percentile * (sortedValues.length - 1))),
  );

  return sortedValues[position] ?? 0;
}

function formatSignedMoodPercent(value: number): string {
  const percentage = value * 100;
  const formatted = percentage.toFixed(1);
  return percentage > 0 ? `+${formatted}%` : `${formatted}%`;
}

function formatMoodLabel(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
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
