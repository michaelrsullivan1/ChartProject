import { useEffect, useMemo, useRef, useState } from "react";

import {
  ColorType,
  LineSeries,
  LineStyle,
  PriceScaleMode,
  createChart,
  type LineData,
  type MouseEventParams,
  type Time,
  type WhitespaceData,
} from "lightweight-charts";

import {
  fetchAggregateMoodCohorts,
  type AggregateMoodCohortsResponse,
} from "../api/authorOverview";
import { fetchPriceMentions, type PriceMentionsResponse } from "../api/priceMentions";
import { PriceMentionCohortSidebar } from "../components/PriceMentionCohortSidebar";
import { DashboardLoadingState } from "../components/DashboardLoadingState";
import {
  ALL_PRICE_MENTION_COHORT_KEY,
  buildPriceMentionCohortOptions,
  buildPriceMentionSelectionHash,
  getPriceMentionCohortTagSlug,
  isValidPriceMentionCohortKey,
  PRICE_MENTION_WINDOW_OPTIONS,
  readPriceMentionUrlState,
  type PriceMentionCohortKey,
  type PriceMentionCohortOption,
  type PriceMentionWindowKey,
} from "../lib/priceMentionCohorts";
import {
  derivePriceMentionSpreadPeriods,
  MIN_PRICE_SPREAD_STRONG_MENTIONS,
  MIN_PRICE_SPREAD_VISIBLE_MENTIONS,
  type PriceMentionSpreadPeriod,
} from "../lib/priceMentionSpread";
import {
  formatWindowLabel,
  resolveWindowedPriceMentionComparison,
} from "../lib/priceMentionWindowing";

const API_BASE = "/api/views";
const PRICE_MENTION_VIEW = "spread";

const compactPriceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});

const detailPriceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
  signDisplay: "exceptZero",
});

const monthDayFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const chartOptions = {
  layout: {
    background: { type: ColorType.Solid, color: "rgba(12, 10, 8, 0)" },
    textColor: "#d4c5ad",
    attributionLogo: false,
  },
  grid: {
    vertLines: { color: "rgba(255, 245, 220, 0.06)" },
    horzLines: { color: "rgba(255, 245, 220, 0.08)" },
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
    rightOffset: 2,
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

type HoverSnapshot = {
  periodLabel: string;
  btcClose: string;
  medianPrice: string;
  iqrBand: string;
  spread: string;
  premium: string;
  predictionCount: string;
  sampleLabel: string;
};

export function PriceMentionSpreadPage() {
  const [data, setData] = useState<PriceMentionsResponse | null>(null);
  const [cohorts, setCohorts] = useState<PriceMentionCohortOption[]>([]);
  const [areCohortsReady, setAreCohortsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [includeLoConfidence, setIncludeLoConfidence] = useState(false);
  const [selectedCohortKey, setSelectedCohortKey] = useState<PriceMentionCohortKey>(
    () =>
      readPriceMentionUrlState(window.location.hash, PRICE_MENTION_VIEW).selectedCohortKey ??
      ALL_PRICE_MENTION_COHORT_KEY,
  );
  const [timeWindow, setTimeWindow] = useState<PriceMentionWindowKey>(
    () => readPriceMentionUrlState(window.location.hash, PRICE_MENTION_VIEW).timeWindow,
  );
  const [hoverSnapshot, setHoverSnapshot] = useState<HoverSnapshot | null>(null);

  const topChartRef = useRef<HTMLDivElement | null>(null);

  const selectedCohortName =
    cohorts.find((cohortOption) => cohortOption.key === selectedCohortKey)?.tagName ??
    "All tracked users";
  const windowedData = resolveWindowedPriceMentionComparison(data, null, timeWindow);
  const spreadPeriods = useMemo(
    () => derivePriceMentionSpreadPeriods(windowedData.selectedPeriods),
    [windowedData.selectedPeriods],
  );
  const latestVisiblePeriod = useMemo(
    () =>
      [...spreadPeriods]
        .reverse()
        .find((period) => period.medianPrice !== null && period.spreadPct !== null) ?? null,
    [spreadPeriods],
  );
  const visiblePeriodCount = spreadPeriods.filter((period) => period.medianPrice !== null).length;
  const lowSampleCount = spreadPeriods.filter((period) => period.sampleStrength === "weak").length;
  const validPeriodStart = windowedData.selectedPeriods[0]?.period_start ?? null;
  const validPeriodEnd =
    windowedData.selectedPeriods[windowedData.selectedPeriods.length - 1]?.period_start ?? null;

  useEffect(() => {
    const ac = new AbortController();
    fetchAggregateMoodCohorts(`${API_BASE}/aggregate-moods`, ac.signal)
      .then((res: AggregateMoodCohortsResponse) => {
        setCohorts(buildPriceMentionCohortOptions(res.cohorts));
      })
      .catch(() => {
        setCohorts(buildPriceMentionCohortOptions([]));
      })
      .finally(() => {
        setAreCohortsReady(true);
      });
    return () => ac.abort();
  }, []);

  useEffect(() => {
    function handleHashChange() {
      const urlState = readPriceMentionUrlState(window.location.hash, PRICE_MENTION_VIEW);
      setSelectedCohortKey(urlState.selectedCohortKey ?? ALL_PRICE_MENTION_COHORT_KEY);
      setTimeWindow(urlState.timeWindow);
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  useEffect(() => {
    const nextHash = buildPriceMentionSelectionHash(
      PRICE_MENTION_VIEW,
      selectedCohortKey,
      null,
      timeWindow,
    );
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  }, [selectedCohortKey, timeWindow]);

  useEffect(() => {
    if (!areCohortsReady) {
      return;
    }

    const effectiveSelectedCohortKey = isValidPriceMentionCohortKey(selectedCohortKey, cohorts)
      ? selectedCohortKey
      : ALL_PRICE_MENTION_COHORT_KEY;
    const ac = new AbortController();
    setIsLoading(true);
    setError(null);

    fetchPriceMentions(
      `${API_BASE}/price-mentions`,
      {
        granularity: "week",
        cohortTag: getPriceMentionCohortTagSlug(effectiveSelectedCohortKey, cohorts),
        minConfidence: includeLoConfidence ? 0.0 : 0.5,
        mentionType: "prediction",
      },
      ac.signal,
    )
      .then((response) => {
        setData(response);
        if (selectedCohortKey !== effectiveSelectedCohortKey) {
          setSelectedCohortKey(effectiveSelectedCohortKey);
        }
        setIsLoading(false);
      })
      .catch((loadError: unknown) => {
        if (loadError instanceof Error && loadError.name === "AbortError") {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Failed to load data");
        setIsLoading(false);
      });

    return () => ac.abort();
  }, [areCohortsReady, cohorts, includeLoConfidence, selectedCohortKey]);

  useEffect(() => {
    if (latestVisiblePeriod) {
      setHoverSnapshot(buildHoverSnapshot(latestVisiblePeriod));
      return;
    }
    setHoverSnapshot(null);
  }, [latestVisiblePeriod]);

  useEffect(() => {
    const topContainer = topChartRef.current;
    if (!topContainer || spreadPeriods.length === 0) {
      return;
    }

    const chartTop = createChart(topContainer, {
      ...chartOptions,
      width: topContainer.clientWidth,
      height: topContainer.clientHeight,
    });
    chartTop.priceScale("right").applyOptions({
      mode: PriceScaleMode.Logarithmic,
      minimumWidth: 76,
      scaleMargins: { top: 0.08, bottom: 0.08 },
    });

    const btcSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(255, 213, 79, 0.9)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerRadius: 3,
      crosshairMarkerVisible: true,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });
    const q25StrongSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(118, 199, 255, 0.5)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });
    const q75StrongSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(118, 199, 255, 0.5)",
      lineWidth: 2,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });
    const medianStrongSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(122, 240, 182, 0.95)",
      lineWidth: 3,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerRadius: 4,
      crosshairMarkerVisible: true,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });
    const q25WeakSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(118, 199, 255, 0.28)",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });
    const q75WeakSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(118, 199, 255, 0.28)",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerVisible: false,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });
    const medianWeakSeries = chartTop.addSeries(LineSeries, {
      color: "rgba(122, 240, 182, 0.48)",
      lineWidth: 2,
      lineStyle: LineStyle.Dashed,
      priceLineVisible: false,
      lastValueVisible: false,
      crosshairMarkerRadius: 3,
      crosshairMarkerVisible: true,
      priceFormat: {
        type: "custom" as const,
        minMove: 1,
        formatter: formatCompactPrice,
      },
    });

    btcSeries.setData(
      spreadPeriods.map<LineData<Time> | WhitespaceData<Time>>((period) =>
        period.btcClose === null
          ? { time: toBusinessDay(period.periodStart) }
          : { time: toBusinessDay(period.periodStart), value: period.btcClose },
      ),
    );
    q25StrongSeries.setData(buildLineData(spreadPeriods, "q25Price", "strong"));
    q75StrongSeries.setData(buildLineData(spreadPeriods, "q75Price", "strong"));
    medianStrongSeries.setData(buildLineData(spreadPeriods, "medianPrice", "strong"));
    q25WeakSeries.setData(buildLineData(spreadPeriods, "q25Price", "weak"));
    q75WeakSeries.setData(buildLineData(spreadPeriods, "q75Price", "weak"));
    medianWeakSeries.setData(buildLineData(spreadPeriods, "medianPrice", "weak"));

    chartTop.timeScale().fitContent();

    const periodLookup = new Map(
      spreadPeriods.map((period) => [period.periodStart.slice(0, 10), period] as const),
    );

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.time) {
        if (latestVisiblePeriod) {
          setHoverSnapshot(buildHoverSnapshot(latestVisiblePeriod));
        }
        return;
      }

      const period = periodLookup.get(resolveBusinessDay(param.time));
      if (!period) {
        return;
      }

      setHoverSnapshot(buildHoverSnapshot(period));
    };

    chartTop.subscribeCrosshairMove(handleCrosshairMove);

    const topObserver = new ResizeObserver(() => {
      chartTop.applyOptions({
        width: topContainer.clientWidth,
        height: topContainer.clientHeight,
      });
    });

    topObserver.observe(topContainer);

    return () => {
      topObserver.disconnect();
      chartTop.remove();
    };
  }, [latestVisiblePeriod, spreadPeriods]);

  return (
    <section className="dashboard-page pm-page pm-comparison-page pm-spread-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          <div>
            <p className="dashboard-eyebrow">Price Mentions — Spread</p>
            <p className="dashboard-subtitle">
              {selectedCohortName} — weekly prediction spread around BTC spot using weighted median
              and IQR
            </p>
          </div>
        </div>

        <div className="pm-controls">
          <div className="chart-control-card pm-comparison-summary-card">
            <p className="chart-control-eyebrow">Metric</p>
            <p className="pm-comparison-summary-copy">
              The chart shows BTC spot with the weekly median prediction and the interquartile
              range.
            </p>
            <p className="chart-control-note">
              Weeks with fewer than {MIN_PRICE_SPREAD_VISIBLE_MENTIONS} prediction mentions are
              hidden. Weeks with {MIN_PRICE_SPREAD_VISIBLE_MENTIONS}-{MIN_PRICE_SPREAD_STRONG_MENTIONS - 1} mentions
              are shown as low-sample dashed lines.
            </p>
          </div>

          <div className="chart-control-card pm-comparison-summary-card">
            <p className="chart-control-eyebrow">Time Window</p>
            <div className="pm-toggle-row pm-toggle-wrap">
              {PRICE_MENTION_WINDOW_OPTIONS.map((option) => (
                <button
                  key={option.key}
                  className={`chart-toggle-button${timeWindow === option.key ? " is-active" : ""}`}
                  onClick={() => setTimeWindow(option.key)}
                  type="button"
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="chart-control-card">
            <p className="chart-control-eyebrow">Confidence</p>
            <div className="pm-toggle-row">
              <button
                className={`chart-toggle-button${!includeLoConfidence ? " is-active" : ""}`}
                onClick={() => setIncludeLoConfidence(false)}
                type="button"
              >
                High + Medium
              </button>
              <button
                className={`chart-toggle-button${includeLoConfidence ? " is-active" : ""}`}
                onClick={() => setIncludeLoConfidence(true)}
                type="button"
              >
                Include Low
              </button>
            </div>
          </div>
        </div>

        <div className="pm-spread-shell">
          <div className="pm-spread-main">
            <div className="pm-spread-stat-grid">
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">Hover week</span>
                <span className="pm-spread-stat-value">
                  {hoverSnapshot?.periodLabel ?? "No active week"}
                </span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">BTC close</span>
                <span className="pm-spread-stat-value">{hoverSnapshot?.btcClose ?? "n/a"}</span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">Median prediction</span>
                <span className="pm-spread-stat-value">
                  {hoverSnapshot?.medianPrice ?? "Insufficient sample"}
                </span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">IQR band</span>
                <span className="pm-spread-stat-value">{hoverSnapshot?.iqrBand ?? "n/a"}</span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">Spread</span>
                <span className="pm-spread-stat-value">{hoverSnapshot?.spread ?? "n/a"}</span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">Median premium</span>
                <span className="pm-spread-stat-value">{hoverSnapshot?.premium ?? "n/a"}</span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">Prediction mentions</span>
                <span className="pm-spread-stat-value">
                  {hoverSnapshot?.predictionCount ?? "0"}
                </span>
              </div>
              <div className="pm-spread-stat-card">
                <span className="pm-spread-stat-label">Sample quality</span>
                <span className="pm-spread-stat-value">{hoverSnapshot?.sampleLabel ?? "n/a"}</span>
              </div>
            </div>

            <div className="pm-spread-chart-stack">
              <div className="chart-shell chart-shell-dashboard pm-spread-chart-shell">
                <div className="pm-spread-chart-header">
                  <div>
                    <p className="chart-control-eyebrow">Prediction Envelope</p>
                    <p className="chart-control-note">
                      BTC spot, weighted median prediction, and interquartile range.
                    </p>
                  </div>
                </div>
                <div className="pm-chart-area pm-spread-chart-area">
                  {isLoading ? (
                    <DashboardLoadingState />
                  ) : error ? (
                    <div className="pm-error">{error}</div>
                  ) : visiblePeriodCount === 0 ? (
                    <div className="pm-empty">
                      No weekly prediction spread coverage found for the selected window.
                    </div>
                  ) : (
                    <div ref={topChartRef} className="pm-lw-chart" />
                  )}
                </div>
              </div>
            </div>

            <div className="pm-legend pm-spread-legend">
              <span className="pm-legend-btc-line" aria-hidden="true" />
              <span className="pm-legend-label">BTC spot</span>
              <span
                className="pm-legend-swatch"
                style={{ background: "rgba(122, 240, 182, 0.95)" }}
                aria-hidden="true"
              />
              <span className="pm-legend-label">Median prediction</span>
              <span
                className="pm-legend-swatch"
                style={{ background: "rgba(118, 199, 255, 0.5)" }}
                aria-hidden="true"
              />
              <span className="pm-legend-label">IQR envelope</span>
              <span className="pm-legend-meta">
                {formatWindowLabel(timeWindow)} · {visiblePeriodCount} visible weeks · {lowSampleCount} low-sample weeks
              </span>
            </div>

            <div className="pm-spread-footnotes">
              <p className="chart-control-note">
                Window coverage: {formatDateLabel(validPeriodStart)} to {formatDateLabel(validPeriodEnd)}.
              </p>
              <p className="chart-control-note">
                Each extracted prediction counts as one vote. Multiple targets in the same tweet are
                counted separately.
              </p>
            </div>
          </div>

          <PriceMentionCohortSidebar
            cohortOptions={cohorts}
            selectedCohortKey={selectedCohortKey}
            pinnedCohortKey={null}
            showPinButtons={false}
            onSelectedCohortKeyChange={setSelectedCohortKey}
            onPinnedCohortKeyToggle={() => {}}
          />
        </div>
      </article>
    </section>
  );
}

function buildLineData(
  periods: PriceMentionSpreadPeriod[],
  field: "medianPrice" | "q25Price" | "q75Price" | "spreadPct",
  strength: "weak" | "strong",
): Array<LineData<Time> | WhitespaceData<Time>> {
  return periods.map((period) => {
    const value = period[field];
    return value !== null && period.sampleStrength === strength
      ? { time: toBusinessDay(period.periodStart), value }
      : { time: toBusinessDay(period.periodStart) };
  });
}

function buildHoverSnapshot(period: PriceMentionSpreadPeriod): HoverSnapshot {
  const sampleLabel =
    period.sampleStrength === "strong"
      ? "Normal"
      : period.sampleStrength === "weak"
        ? "Low sample"
        : "Hidden";

  return {
    periodLabel: formatDateLabel(period.periodStart),
    btcClose: period.btcClose !== null ? detailPriceFormatter.format(period.btcClose) : "n/a",
    medianPrice:
      period.medianPrice !== null ? detailPriceFormatter.format(period.medianPrice) : "Insufficient sample",
    iqrBand:
      period.q25Price !== null && period.q75Price !== null
        ? `${detailPriceFormatter.format(period.q25Price)} to ${detailPriceFormatter.format(period.q75Price)}`
        : "Insufficient sample",
    spread: period.spreadPct !== null ? formatPercentValue(period.spreadPct) : "n/a",
    premium: period.medianPremiumPct !== null ? formatPercentValue(period.medianPremiumPct) : "n/a",
    predictionCount: `${period.predictionCount}`,
    sampleLabel,
  };
}

function formatCompactPrice(value: number): string {
  return compactPriceFormatter.format(value);
}

function formatPercentValue(value: number): string {
  return `${percentFormatter.format(value)}%`;
}

function formatDateLabel(value: string | null): string {
  return value ? monthDayFormatter.format(new Date(value)) : "n/a";
}

function resolveBusinessDay(time: Time): string {
  if (typeof time === "string") {
    return time;
  }
  if (typeof time === "object" && "year" in time) {
    return `${time.year}-${`${time.month}`.padStart(2, "0")}-${`${time.day}`.padStart(2, "0")}`;
  }
  return "";
}

function toBusinessDay(value: string): Time {
  return value.slice(0, 10) as Time;
}
