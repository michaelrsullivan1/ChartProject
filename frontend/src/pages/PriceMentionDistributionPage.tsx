import { useEffect, useRef, useState } from "react";
import {
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type LineData,
  type Time,
  type UTCTimestamp,
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
  getNextPinnedPriceMentionCohortKey,
  getPinnedPriceMentionComparisonKey,
  getPriceMentionCohortTagSlug,
  isValidPriceMentionCohortKey,
  PRICE_MENTION_WINDOW_OPTIONS,
  readPriceMentionUrlState,
  type PriceMentionCohortKey,
  type PriceMentionCohortOption,
  type PriceMentionWindowKey,
} from "../lib/priceMentionCohorts";
import {
  aggregatePriceMentionPeriodsIntoBuckets,
  formatWindowLabel,
  resolveWindowedPriceMentionComparison,
} from "../lib/priceMentionWindowing";

const API_BASE = "/api/views";

const MENTION_TYPES = ["prediction", "conditional", "current", "historical", "unclassified"] as const;
type MentionTypeFilter = "all" | (typeof MENTION_TYPES)[number];

const PRICE_BUCKETS = [
  10_000, 20_000, 30_000, 40_000, 50_000, 60_000, 70_000, 80_000, 90_000, 100_000,
  125_000, 150_000, 175_000, 200_000, 250_000, 300_000, 400_000, 500_000,
  750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000,
];

const FAKE_EPOCH = 946684800;
const FAKE_DAY = 86400;
const PRICE_MENTION_VIEW = "distribution";

const compactPriceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 0,
});

function bucketIndexToTime(index: number): UTCTimestamp {
  return (FAKE_EPOCH + index * FAKE_DAY) as UTCTimestamp;
}

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
  rightPriceScale: { borderVisible: false },
  crosshair: {
    vertLine: { color: "rgba(255, 178, 64, 0.28)", labelBackgroundColor: "#4d2f17" },
    horzLine: { color: "rgba(118, 199, 255, 0.24)", labelBackgroundColor: "#1f3443" },
  },
  timeScale: {
    borderVisible: false,
    tickMarkFormatter: (time: Time) => {
      const t = typeof time === "number" ? time : 0;
      const index = Math.round((t - FAKE_EPOCH) / FAKE_DAY);
      if (index < 0 || index >= PRICE_BUCKETS.length) return "";
      return compactPriceFormatter.format(PRICE_BUCKETS[index]);
    },
  },
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
    horzTouchDrag: true,
    vertTouchDrag: false,
  },
  handleScale: {
    axisPressedMouseMove: { time: true, price: false },
    mouseWheel: true,
    pinch: true,
  },
};

export function PriceMentionDistributionPage() {
  const [data, setData] = useState<PriceMentionsResponse | null>(null);
  const [comparisonData, setComparisonData] = useState<PriceMentionsResponse | null>(null);
  const [cohorts, setCohorts] = useState<PriceMentionCohortOption[]>([]);
  const [areCohortsReady, setAreCohortsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mentionType, setMentionType] = useState<MentionTypeFilter>("all");
  const [includeLoConfidence, setIncludeLoConfidence] = useState(false);
  const [selectedCohortKey, setSelectedCohortKey] = useState<PriceMentionCohortKey>(
    () =>
      readPriceMentionUrlState(window.location.hash, PRICE_MENTION_VIEW).selectedCohortKey ??
      ALL_PRICE_MENTION_COHORT_KEY,
  );
  const [pinnedCohortKey, setPinnedCohortKey] = useState<PriceMentionCohortKey | null>(
    () => readPriceMentionUrlState(window.location.hash, PRICE_MENTION_VIEW).pinnedCohortKey,
  );
  const [timeWindow, setTimeWindow] = useState<PriceMentionWindowKey>(
    () => readPriceMentionUrlState(window.location.hash, PRICE_MENTION_VIEW).timeWindow,
  );

  const containerRef = useRef<HTMLDivElement>(null);

  const selectedCohortName =
    cohorts.find((cohortOption) => cohortOption.key === selectedCohortKey)?.tagName ??
    "All tracked users";
  const effectivePinnedComparisonKey = getPinnedPriceMentionComparisonKey(
    selectedCohortKey,
    pinnedCohortKey,
  );
  const fallbackComparisonKey =
    effectivePinnedComparisonKey ??
    (selectedCohortKey === ALL_PRICE_MENTION_COHORT_KEY ? null : ALL_PRICE_MENTION_COHORT_KEY);
  const comparisonCohortName =
    fallbackComparisonKey === null
      ? null
      : cohorts.find((cohortOption) => cohortOption.key === fallbackComparisonKey)?.tagName ??
        "All tracked users";
  const windowedComparison = resolveWindowedPriceMentionComparison(data, comparisonData, timeWindow);

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
      setPinnedCohortKey(urlState.pinnedCohortKey);
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
      pinnedCohortKey,
      timeWindow,
    );
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  }, [pinnedCohortKey, selectedCohortKey, timeWindow]);

  useEffect(() => {
    if (!areCohortsReady) {
      return;
    }

    const ac = new AbortController();
    setIsLoading(true);
    setError(null);

    const effectiveSelectedCohortKey = isValidPriceMentionCohortKey(selectedCohortKey, cohorts)
      ? selectedCohortKey
      : ALL_PRICE_MENTION_COHORT_KEY;
    const effectivePinnedCohortKey =
      pinnedCohortKey !== null && isValidPriceMentionCohortKey(pinnedCohortKey, cohorts)
        ? pinnedCohortKey
        : null;
    const effectiveComparisonCohortKey =
      getPinnedPriceMentionComparisonKey(effectiveSelectedCohortKey, effectivePinnedCohortKey) ??
      (effectiveSelectedCohortKey === ALL_PRICE_MENTION_COHORT_KEY
        ? null
        : ALL_PRICE_MENTION_COHORT_KEY);
    const params = {
      granularity: "month" as const,
      cohortTag: getPriceMentionCohortTagSlug(effectiveSelectedCohortKey, cohorts),
      minConfidence: includeLoConfidence ? 0.0 : 0.5,
      mentionType: mentionType === "all" ? null : mentionType,
    };

    const comparisonPromise = effectiveComparisonCohortKey
      ? fetchPriceMentions(
          `${API_BASE}/price-mentions`,
          {
            ...params,
            cohortTag: getPriceMentionCohortTagSlug(effectiveComparisonCohortKey, cohorts),
          },
          ac.signal,
        )
      : Promise.resolve(null);

    Promise.all([
      fetchPriceMentions(`${API_BASE}/price-mentions`, params, ac.signal),
      comparisonPromise,
    ])
      .then(([primary, comparison]) => {
        setData(primary);
        setComparisonData(comparison);
        if (selectedCohortKey !== effectiveSelectedCohortKey) {
          setSelectedCohortKey(effectiveSelectedCohortKey);
        }
        if (pinnedCohortKey !== effectivePinnedCohortKey) {
          setPinnedCohortKey(effectivePinnedCohortKey);
        }
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load data");
        setIsLoading(false);
      });

    return () => ac.abort();
  }, [
    areCohortsReady,
    cohorts,
    includeLoConfidence,
    mentionType,
    pinnedCohortKey,
    selectedCohortKey,
  ]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !data) return;

    const cohortBuckets = aggregatePriceMentionPeriodsIntoBuckets(
      windowedComparison.selectedPeriods,
      PRICE_BUCKETS,
    );
    const cohortTotal = cohortBuckets.reduce((s, c) => s + c, 0);

    const comparisonBuckets = comparisonData
      ? aggregatePriceMentionPeriodsIntoBuckets(windowedComparison.comparisonPeriods, PRICE_BUCKETS)
      : null;
    const comparisonTotal = comparisonBuckets ? comparisonBuckets.reduce((s, c) => s + c, 0) : 0;

    const cohortSeries: LineData<Time>[] = PRICE_BUCKETS.map((_, i) => ({
      time: bucketIndexToTime(i) as Time,
      value: cohortTotal > 0 ? (cohortBuckets[i] / cohortTotal) * 100 : 0,
    }));

    const comparisonSeries: LineData<Time>[] =
      comparisonBuckets && comparisonTotal > 0
        ? PRICE_BUCKETS.map((_, i) => ({
            time: bucketIndexToTime(i) as Time,
            value: (comparisonBuckets[i] / comparisonTotal) * 100,
          }))
        : [];

    const chart = createChart(container, {
      ...chartOptions,
      width: container.clientWidth,
      height: container.clientHeight,
    });

    if (comparisonSeries.length > 0) {
      const comparisonLine = chart.addSeries(LineSeries, {
        color: "rgba(198, 191, 180, 0.7)",
        lineWidth: 1,
        lineType: LineType.WithSteps,
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        priceFormat: { type: "percent" as const },
      });
      comparisonLine.setData(comparisonSeries);
    }

    const cohortLine = chart.addSeries(LineSeries, {
      color: "rgba(100, 160, 255, 0.9)",
      lineWidth: 2,
      lineType: LineType.WithSteps,
      lastValueVisible: false,
      priceLineVisible: false,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 4,
      crosshairMarkerBorderWidth: 1,
      crosshairMarkerBorderColor: "rgba(100, 160, 255, 0.9)",
      crosshairMarkerBackgroundColor: "#17130f",
      priceFormat: { type: "percent" as const },
    });
    cohortLine.setData(cohortSeries);

    chart.priceScale("right").applyOptions({
      autoScale: true,
      scaleMargins: { top: 0.08, bottom: 0.08 },
      minimumWidth: 64,
    });
    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      chart.applyOptions({ width: container.clientWidth, height: container.clientHeight });
    });
    observer.observe(container);

    return () => {
      observer.disconnect();
      chart.remove();
    };
  }, [comparisonData, data, windowedComparison.comparisonPeriods, windowedComparison.selectedPeriods]);

  const totalMentions =
    windowedComparison.selectedPeriods.length > 0 ? windowedComparison.selectedMentionCount : null;

  function handleSelectedCohortKeyChange(nextKey: PriceMentionCohortKey) {
    if (selectedCohortKey === nextKey) {
      return;
    }

    setPinnedCohortKey((currentPinnedKey) =>
      getNextPinnedPriceMentionCohortKey(selectedCohortKey, currentPinnedKey, nextKey),
    );
    setSelectedCohortKey(nextKey);
  }

  function handlePinnedCohortKeyToggle(nextKey: PriceMentionCohortKey) {
    setPinnedCohortKey((currentPinnedKey) => (currentPinnedKey === nextKey ? null : nextKey));
  }

  return (
    <section className="dashboard-page pm-page pm-comparison-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          <div>
            <p className="dashboard-eyebrow">Price Mentions — Distribution</p>
            <p className="dashboard-subtitle">
              {comparisonCohortName
                ? `${selectedCohortName} vs. ${comparisonCohortName} — price level distribution`
                : `${selectedCohortName} — price level distribution`}
            </p>
          </div>
        </div>

        <div className="pm-controls">
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
            <p className="pm-comparison-summary-copy">
              {windowedComparison.coverageSummary ?? `${formatWindowLabel(timeWindow)} window.`}
            </p>
            {windowedComparison.coverageNote ? (
              <p className="chart-control-note">{windowedComparison.coverageNote}</p>
            ) : null}
            {windowedComparison.timingNote ? (
              <p className="chart-control-note">{windowedComparison.timingNote}</p>
            ) : null}
          </div>

          <div className="chart-control-card">
            <p className="chart-control-eyebrow">Mention Type</p>
            <div className="pm-toggle-row pm-toggle-wrap">
              <button
                className={`chart-toggle-button${mentionType === "all" ? " is-active" : ""}`}
                onClick={() => setMentionType("all")}
                type="button"
              >All</button>
              {MENTION_TYPES.map((t) => (
                <button
                  key={t}
                  className={`chart-toggle-button${mentionType === t ? " is-active" : ""}`}
                  onClick={() => setMentionType(t)}
                  type="button"
                >
                  {t.charAt(0).toUpperCase() + t.slice(1)}
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
              >High + Medium</button>
              <button
                className={`chart-toggle-button${includeLoConfidence ? " is-active" : ""}`}
                onClick={() => setIncludeLoConfidence(true)}
                type="button"
              >Include Low</button>
            </div>
          </div>
        </div>

        <div className="pm-comparison-shell">
          <div className="pm-comparison-chart-column">
            <div className="pm-chart-area">
              {isLoading ? (
                <DashboardLoadingState />
              ) : error ? (
                <div className="pm-error">{error}</div>
              ) : windowedComparison.selectedPeriods.length === 0 ? (
                <div className="pm-empty">No price mention coverage found for the selected window.</div>
              ) : data && data.periods.length === 0 ? (
                <div className="pm-empty">No price mentions found for the selected filters.</div>
              ) : (
                <div ref={containerRef} className="pm-lw-chart" />
              )}
            </div>

            <div className="pm-legend">
              <span className="pm-legend-swatch pm-legend-swatch-cohort" aria-hidden="true" />
              <span className="pm-legend-label">{selectedCohortName}</span>
              {comparisonCohortName ? (
                <>
                  <span className="pm-legend-swatch pm-legend-swatch-baseline" aria-hidden="true" />
                  <span className="pm-legend-label">{comparisonCohortName}</span>
                </>
              ) : null}
              {totalMentions !== null ? (
                <span className="pm-legend-meta">
                  {formatWindowLabel(timeWindow)} · {totalMentions.toLocaleString()} mentions for{" "}
                  {selectedCohortName}
                </span>
              ) : null}
            </div>
          </div>

          <PriceMentionCohortSidebar
            cohortOptions={cohorts}
            selectedCohortKey={selectedCohortKey}
            pinnedCohortKey={pinnedCohortKey}
            onSelectedCohortKeyChange={handleSelectedCohortKeyChange}
            onPinnedCohortKeyToggle={handlePinnedCohortKeyToggle}
          />
        </div>
      </article>
    </section>
  );
}
