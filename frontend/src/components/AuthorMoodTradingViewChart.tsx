import { type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Expand, X } from "lucide-react";

import {
  BaselineSeries,
  ColorType,
  HistogramSeries,
  LineSeries,
  LineType,
  createChart,
  type BaselineData,
  type HistogramData,
  type LineData,
  type Time,
  type WhitespaceData,
} from "lightweight-charts";

import type { AuthorMoodResponse, AuthorOverviewResponse } from "../api/authorOverview";
import { ChartControlSelect } from "./ChartControlSelect";
import { buildMoodDeviationSeries } from "../lib/moods";
import type { SentimentMode } from "../lib/sentiment";
import { CHART_WATERMARK_HANDLE } from "../lib/watermark";

type AuthorMoodTradingViewChartProps = {
  payload: AuthorOverviewResponse;
  moodPayload: AuthorMoodResponse;
  comparisonMoodPayload?: AuthorMoodResponse | null;
  comparisonMoodLabel?: string | null;
  comparisonMoodColor?: string;
  selectedMoodLabel: string;
  priceMode: PriceMode;
  moodVisualMode: MoodVisualMode;
  showWatermark: boolean;
  showMoodSelector?: boolean;
  moodSelectorVariant?: "buttons" | "select";
  moodDefinition?: string;
  rightSidebarSupplementalContent?: ReactNode;
  rightSidebarContent?: ReactNode;
  sentimentMode: SentimentMode;
  smoothingWeightLabel?: string;
  onPriceModeChange: (mode: PriceMode) => void;
  onMoodVisualModeChange: (mode: MoodVisualMode) => void;
  onSentimentModeChange: (mode: SentimentMode) => void;
  onMoodLabelChange: (label: string) => void;
};

export type PriceMode = "btc" | "mstr" | "both";
export type MoodVisualMode = "line" | "bars";
type MoodSeriesPoint = BaselineData<Time> | WhitespaceData<Time>;
type MoodHistogramPoint = HistogramData<Time> | WhitespaceData<Time>;

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
  comparisonMoodPayload = null,
  comparisonMoodLabel,
  comparisonMoodColor = "rgba(198, 191, 180, 0.8)",
  selectedMoodLabel,
  priceMode,
  moodVisualMode,
  showWatermark,
  showMoodSelector = true,
  moodSelectorVariant = "buttons",
  moodDefinition,
  rightSidebarSupplementalContent,
  rightSidebarContent,
  sentimentMode,
  smoothingWeightLabel = "scored post count",
  onPriceModeChange,
  onMoodVisualModeChange,
  onSentimentModeChange,
  onMoodLabelChange,
}: AuthorMoodTradingViewChartProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const btcSeriesData = useMemo(() => buildBtcSeries(payload), [payload]);
  const mstrSeriesData = useMemo(() => buildMstrSeries(payload), [payload]);
  const moodDeviationSeries = useMemo(
    () => buildMoodDeviationSeries(moodPayload, selectedMoodLabel, sentimentMode),
    [moodPayload, selectedMoodLabel, sentimentMode],
  );
  const comparisonMoodDeviationSeries = useMemo(
    () =>
      comparisonMoodPayload
        ? buildMoodDeviationSeries(comparisonMoodPayload, selectedMoodLabel, sentimentMode)
        : [],
    [comparisonMoodPayload, selectedMoodLabel, sentimentMode],
  );
  const moodSeriesData = useMemo<MoodSeriesPoint[]>(
    () => moodDeviationSeries.map((point) => buildMoodSeriesPoint(point.periodStart, point.value)),
    [moodDeviationSeries],
  );
  const comparisonMoodSeriesData = useMemo<LineData<Time>[]>(
    () =>
      comparisonMoodDeviationSeries.flatMap((point) => {
        const time = toBusinessDay(point.periodStart);
        return point.value === null ? [] : [{ time, value: point.value }];
      }),
    [comparisonMoodDeviationSeries],
  );
  const moodHistogramData = useMemo<MoodHistogramPoint[]>(
    () =>
      moodDeviationSeries.map((point) => {
        const time = toBusinessDay(point.periodStart);
        if (point.value === null) {
          return { time };
        }

        return {
          time,
          value: point.value,
          color: point.value > 0 ? "rgba(122, 240, 182, 0.72)" : "rgba(255, 108, 108, 0.72)",
        };
      }),
    [moodDeviationSeries],
  );
  const moodRange = useMemo(
    () => buildSymmetricMoodRange([...moodSeriesData, ...comparisonMoodSeriesData], sentimentMode),
    [comparisonMoodSeriesData, moodSeriesData, sentimentMode],
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

    if (moodVisualMode === "bars") {
      const moodBarsSeries = chart.addSeries(
        HistogramSeries,
        {
          title: "",
          base: 0,
          lastValueVisible: false,
          priceLineVisible: false,
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
      moodBarsSeries.setData(moodHistogramData);
    } else {
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
          lineType: LineType.Simple,
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
      moodSeries.setData(moodSeriesData);
    }

    if (comparisonMoodSeriesData.length > 0) {
      const comparisonSeries = chart.addSeries(
        LineSeries,
        {
          title: "",
          color: comparisonMoodColor,
          lineWidth: 2,
          lineType: LineType.Simple,
          lastValueVisible: false,
          priceLineVisible: false,
          crosshairMarkerVisible: false,
          priceFormat: {
            type: "custom",
            minMove: 0.001,
            formatter: formatSignedMoodPercent,
          },
        },
        1,
      );
      comparisonSeries.setData(comparisonMoodSeriesData);
    }

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
        top: 0.12,
        bottom: 0.12,
      },
    });

    btcSeries.setData(priceMode === "mstr" ? [] : btcSeriesData);
    mstrSeries.setData(priceMode === "btc" ? [] : mstrSeriesData);

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
  }, [
    btcSeriesData,
    comparisonMoodColor,
    comparisonMoodLabel,
    comparisonMoodSeriesData,
    isFullscreen,
    moodHistogramData,
    moodRange,
    moodSeriesData,
    moodVisualMode,
    mstrSeriesData,
    priceMode,
  ]);

  useEffect(() => {
    if (!isFullscreen) {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setIsFullscreen(false);
      }
    }

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isFullscreen]);

  const chartStage = (
    <div className={`chart-stage${isFullscreen ? " chart-stage-fullscreen" : ""}`}>
      <button
        aria-label={isFullscreen ? "Close fullscreen chart" : "Open fullscreen chart"}
        className="chart-fullscreen-button"
        onClick={() => setIsFullscreen((current) => !current)}
        title={isFullscreen ? "Close fullscreen" : "Open fullscreen"}
        type="button"
      >
        {isFullscreen ? (
          <X aria-hidden="true" size={16} strokeWidth={2} />
        ) : (
          <Expand aria-hidden="true" size={16} strokeWidth={2} />
        )}
      </button>
      {showWatermark ? (
        <div aria-hidden="true" className="chart-watermark">
          <span className="chart-watermark-handle">{CHART_WATERMARK_HANDLE}</span>
        </div>
      ) : null}
      <div className="tradingview-chart" ref={containerRef} />
    </div>
  );

  const chartLayout = (
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
                onClick={() => onPriceModeChange(mode)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Mood View</p>
          <div className="chart-toggle-group chart-toggle-group-compact" role="group" aria-label="Mood view">
            {(
              [
                ["line", "Line"],
                ["bars", "Bars"],
              ] as const
            ).map(([mode, label]) => (
              <button
                key={mode}
                className={`chart-toggle-button${moodVisualMode === mode ? " is-active" : ""}`}
                onClick={() => onMoodVisualModeChange(mode)}
                type="button"
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Mood Mode</p>
          <div className="chart-toggle-group" role="group" aria-label="Mood smoothing mode">
            {(
              [
                ["weighted-4w", "4W WMA"],
                ["weighted-8w", "8W WMA"],
                ["weighted-12w", "12W WMA"],
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
            WMA modes weight trailing weekly averages by {smoothingWeightLabel}.
          </p>
        </div>
        {moodDefinition ? (
          <div className="chart-control-card">
            <p className="chart-control-eyebrow">Mood Definition</p>
            <p className="chart-control-note">{moodDefinition}</p>
          </div>
        ) : null}
      </aside>

      {chartStage}

      {showMoodSelector || rightSidebarSupplementalContent || rightSidebarContent ? (
        <aside className="chart-sidebar">
          {showMoodSelector ? (
            <>
              <div className="chart-control-card">
                <p className="chart-control-eyebrow">Mood</p>
                {moodSelectorVariant === "select" ? (
                  <label className="chart-control-field">
                    <span className="sr-only">Mood label</span>
                    <ChartControlSelect
                      ariaLabel="Mood label"
                      onChange={onMoodLabelChange}
                      options={moodPayload.model.mood_labels.map((moodLabel) => ({
                        value: moodLabel,
                        label: formatMoodLabel(moodLabel),
                      }))}
                      value={selectedMoodLabel}
                    />
                  </label>
                ) : (
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
                )}
              </div>
              {rightSidebarSupplementalContent}
            </>
          ) : (
            rightSidebarContent
          )}
        </aside>
      ) : null}
    </div>
  );

  return (
    <>
      {!isFullscreen ? chartLayout : null}
      {isFullscreen
        ? createPortal(
            <div
              aria-label="Fullscreen mood chart"
              className="chart-fullscreen-overlay"
              onClick={() => setIsFullscreen(false)}
              role="dialog"
            >
              <div
                className="chart-fullscreen-content"
                onClick={(event) => event.stopPropagation()}
              >
                {chartStage}
              </div>
            </div>,
            document.body,
          )
        : null}
    </>
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

function buildMoodSeriesPoint(periodStart: string, value: number | null): MoodSeriesPoint {
  const time = toBusinessDay(periodStart);
  if (value === null) {
    return { time };
  }

  return {
    time,
    value,
  };
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
