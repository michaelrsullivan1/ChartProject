import { useEffect, useRef, useState } from "react";

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
import { PRICE_MENTION_BUCKETS } from "../lib/priceMentionBuckets";

const API_BASE = "/api/views";

const MENTION_TYPES = ["prediction", "conditional", "current", "historical", "unclassified"] as const;
type MentionTypeFilter = "all" | (typeof MENTION_TYPES)[number];

const PRICE_MENTION_VIEW = "distribution";

const compactPriceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 0,
});

const percentFormatter = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 1,
});

const hoverPriceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 0,
});

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
  const [visibleBucketRange, setVisibleBucketRange] = useState(() => ({
    start: 0,
    end: PRICE_MENTION_BUCKETS.length - 1,
  }));

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const drawRef = useRef<(() => void) | null>(null);
  const hoveredBucketIndexRef = useRef<number | null>(null);
  const dragStateRef = useRef<{ pointerId: number; lastClientX: number } | null>(null);

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
    setVisibleBucketRange({ start: 0, end: PRICE_MENTION_BUCKETS.length - 1 });
    hoveredBucketIndexRef.current = null;
  }, [comparisonData, data, includeLoConfidence, mentionType, selectedCohortKey, pinnedCohortKey, timeWindow]);

  useEffect(() => {
    drawRef.current = () => {
      if (!canvasRef.current || !containerRef.current) {
        return;
      }

      const canvas = canvasRef.current;
      const container = containerRef.current;
      const width = container.clientWidth;
      const height = container.clientHeight;
      if (width === 0 || height === 0) {
        return;
      }

      const selectedBuckets = aggregatePriceMentionPeriodsIntoBuckets(
        windowedComparison.selectedPeriods,
        PRICE_MENTION_BUCKETS,
      );
      const comparisonBuckets = comparisonData
        ? aggregatePriceMentionPeriodsIntoBuckets(
            windowedComparison.comparisonPeriods,
            PRICE_MENTION_BUCKETS,
          )
        : null;
      const selectedTotal = selectedBuckets.reduce((sum, count) => sum + count, 0);
      const comparisonTotal = comparisonBuckets
        ? comparisonBuckets.reduce((sum, count) => sum + count, 0)
        : 0;
      const selectedValues = PRICE_MENTION_BUCKETS.map((_, index) =>
        selectedTotal > 0 ? (selectedBuckets[index] / selectedTotal) * 100 : 0,
      );
      const comparisonValues =
        comparisonBuckets && comparisonTotal > 0
          ? PRICE_MENTION_BUCKETS.map(
              (_, index) => (comparisonBuckets[index] / comparisonTotal) * 100,
            )
          : null;

      const dpr = window.devicePixelRatio || 1;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;

      const ctx = canvas.getContext("2d");
      if (!ctx) {
        return;
      }

      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      drawGroupedDistributionChart(
        ctx,
        width,
        height,
        selectedValues,
        comparisonValues,
        hoveredBucketIndexRef.current,
        visibleBucketRange,
      );
    };

    drawRef.current();
  }, [
    comparisonData,
    visibleBucketRange,
    windowedComparison.comparisonPeriods,
    windowedComparison.selectedPeriods,
  ]);

  const isChartVisible =
    !isLoading &&
    !error &&
    windowedComparison.selectedPeriods.length > 0 &&
    !(data && data.periods.length === 0);

  useEffect(() => {
    if (!isChartVisible || !containerRef.current) {
      return;
    }

    const container = containerRef.current;

    function handlePointerLeave() {
      if (dragStateRef.current !== null) {
        return;
      }
      hoveredBucketIndexRef.current = null;
      drawRef.current?.();
    }

    function handlePointerMove(event: PointerEvent) {
      const rect = container.getBoundingClientRect();
      const localX = event.clientX - rect.left;
      const localY = event.clientY - rect.top;
      const chartWidth = rect.width - DIST_CHART_LEFT - DIST_CHART_RIGHT;
      const chartHeight = rect.height - DIST_CHART_TOP - DIST_CHART_BOTTOM;
      const chartLeft = DIST_CHART_LEFT;
      const chartRight = DIST_CHART_LEFT + chartWidth;
      const activeDrag = dragStateRef.current;
      if (activeDrag && activeDrag.pointerId === event.pointerId) {
        if (chartWidth <= 0) {
          return;
        }

        const visibleBucketCount = visibleBucketRange.end - visibleBucketRange.start + 1;
        const bucketDelta = ((event.clientX - activeDrag.lastClientX) / chartWidth) * visibleBucketCount;
        dragStateRef.current = { pointerId: event.pointerId, lastClientX: event.clientX };
        if (bucketDelta !== 0) {
          setVisibleBucketRange((currentRange) =>
            clampVisibleBucketRange({
              start: currentRange.start - bucketDelta,
              end: currentRange.end - bucketDelta,
            }),
          );
        }
        return;
      }
      if (
        chartWidth <= 0 ||
        chartHeight <= 0 ||
        localX < chartLeft ||
        localX > chartRight ||
        localY < DIST_CHART_TOP ||
        localY > DIST_CHART_TOP + chartHeight
      ) {
        if (hoveredBucketIndexRef.current !== null) {
          hoveredBucketIndexRef.current = null;
          drawRef.current?.();
        }
        return;
      }

      const relativeX = localX - chartLeft;
      const bucketIndex = bucketIndexFromChartX(relativeX, chartWidth, visibleBucketRange);
      if (hoveredBucketIndexRef.current !== bucketIndex) {
        hoveredBucketIndexRef.current = bucketIndex;
        drawRef.current?.();
      }
    }

    function handlePointerDown(event: PointerEvent) {
      const rect = container.getBoundingClientRect();
      const localX = event.clientX - rect.left;
      const localY = event.clientY - rect.top;
      const chartWidth = rect.width - DIST_CHART_LEFT - DIST_CHART_RIGHT;
      const chartHeight = rect.height - DIST_CHART_TOP - DIST_CHART_BOTTOM;
      if (
        chartWidth <= 0 ||
        chartHeight <= 0 ||
        localX < DIST_CHART_LEFT ||
        localX > DIST_CHART_LEFT + chartWidth ||
        localY < DIST_CHART_TOP ||
        localY > DIST_CHART_TOP + chartHeight
      ) {
        return;
      }

      dragStateRef.current = { pointerId: event.pointerId, lastClientX: event.clientX };
      container.setPointerCapture(event.pointerId);
    }

    function handlePointerUp(event: PointerEvent) {
      if (dragStateRef.current?.pointerId !== event.pointerId) {
        return;
      }
      dragStateRef.current = null;
      if (container.hasPointerCapture(event.pointerId)) {
        container.releasePointerCapture(event.pointerId);
      }
    }

    function handleWheel(event: WheelEvent) {
      const rect = container.getBoundingClientRect();
      const localX = event.clientX - rect.left;
      const chartWidth = rect.width - DIST_CHART_LEFT - DIST_CHART_RIGHT;
      const chartHeight = rect.height - DIST_CHART_TOP - DIST_CHART_BOTTOM;
      if (
        chartWidth <= 0 ||
        chartHeight <= 0 ||
        localX < DIST_CHART_LEFT ||
        localX > DIST_CHART_LEFT + chartWidth
      ) {
        return;
      }

      event.preventDefault();
      const zoomFactor =
        event.deltaY > 0 ? DIST_WHEEL_ZOOM_FACTOR : 1 / DIST_WHEEL_ZOOM_FACTOR;
      const anchorRatio = (localX - DIST_CHART_LEFT) / chartWidth;
      setVisibleBucketRange((currentRange) =>
        zoomVisibleBucketRange(currentRange, zoomFactor, anchorRatio),
      );
    }

    function handleDoubleClick() {
      setVisibleBucketRange({ start: 0, end: PRICE_MENTION_BUCKETS.length - 1 });
    }

    const observer = new ResizeObserver(() => {
      drawRef.current?.();
    });
    observer.observe(container);
    container.addEventListener("pointerdown", handlePointerDown);
    container.addEventListener("pointerleave", handlePointerLeave);
    container.addEventListener("pointermove", handlePointerMove);
    container.addEventListener("pointerup", handlePointerUp);
    container.addEventListener("pointercancel", handlePointerUp);
    container.addEventListener("wheel", handleWheel, { passive: false });
    container.addEventListener("dblclick", handleDoubleClick);
    return () => {
      observer.disconnect();
      container.removeEventListener("pointerdown", handlePointerDown);
      container.removeEventListener("pointerleave", handlePointerLeave);
      container.removeEventListener("pointermove", handlePointerMove);
      container.removeEventListener("pointerup", handlePointerUp);
      container.removeEventListener("pointercancel", handlePointerUp);
      container.removeEventListener("wheel", handleWheel);
      container.removeEventListener("dblclick", handleDoubleClick);
    };
  }, [data, error, isChartVisible, isLoading, visibleBucketRange, windowedComparison.selectedPeriods.length]);

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
                <div ref={containerRef} className="pm-chart-canvas-shell">
                  <canvas ref={canvasRef} className="pm-canvas" />
                </div>
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
              {windowedComparison.selectedPeriods.length > 0 ? (
                <span className="pm-legend-meta">
                  {formatWindowLabel(timeWindow)} for {selectedCohortName}
                </span>
              ) : null}
              <span className="pm-legend-meta">Scroll to zoom, drag to pan, double-click to reset</span>
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

const DIST_CHART_LEFT = 56;
const DIST_CHART_RIGHT = 16;
const DIST_CHART_TOP = 12;
const DIST_CHART_BOTTOM = 44;
const DIST_TICK_COUNT = 5;
const SELECTED_BAR_COLOR = "rgba(100, 160, 255, 0.88)";
const COMPARISON_BAR_COLOR = "rgba(198, 191, 180, 0.8)";
const DIST_WHEEL_ZOOM_FACTOR = 1.02;

function drawGroupedDistributionChart(
  ctx: CanvasRenderingContext2D,
  totalWidth: number,
  totalHeight: number,
  selectedValues: number[],
  comparisonValues: number[] | null,
  hoveredBucketIndex: number | null,
  visibleBucketRange: { start: number; end: number },
) {
  ctx.clearRect(0, 0, totalWidth, totalHeight);

  const chartWidth = totalWidth - DIST_CHART_LEFT - DIST_CHART_RIGHT;
  const chartHeight = totalHeight - DIST_CHART_TOP - DIST_CHART_BOTTOM;
  if (chartWidth <= 0 || chartHeight <= 0 || selectedValues.length === 0) {
    return;
  }

  const hasComparison = comparisonValues !== null;
  const allValues = hasComparison ? [...selectedValues, ...comparisonValues] : selectedValues;
  const visibleStartIndex = Math.max(0, Math.floor(visibleBucketRange.start));
  const visibleEndIndex = Math.min(PRICE_MENTION_BUCKETS.length - 1, Math.ceil(visibleBucketRange.end));
  const visibleSelectedValues = selectedValues.slice(visibleStartIndex, visibleEndIndex + 1);
  const visibleComparisonValues =
    comparisonValues?.slice(visibleStartIndex, visibleEndIndex + 1) ?? null;
  const visibleAllValues = visibleComparisonValues
    ? [...visibleSelectedValues, ...visibleComparisonValues]
    : visibleSelectedValues;
  const maxValue = Math.max(...visibleAllValues, 0);
  const yMax = roundUpDistributionMax(maxValue);

  ctx.fillStyle = "rgba(0, 0, 0, 0.16)";
  ctx.fillRect(DIST_CHART_LEFT, DIST_CHART_TOP, chartWidth, chartHeight);

  drawDistributionGrid(ctx, chartWidth, chartHeight, yMax);
  drawDistributionBars(
    ctx,
    chartWidth,
    chartHeight,
    selectedValues,
    comparisonValues,
    yMax,
    visibleBucketRange,
  );
  drawDistributionXAxis(ctx, chartWidth, chartHeight, visibleBucketRange);
  if (
    hoveredBucketIndex !== null &&
    hoveredBucketIndex >= visibleStartIndex &&
    hoveredBucketIndex <= visibleEndIndex
  ) {
    drawDistributionHover(ctx, chartWidth, chartHeight, hoveredBucketIndex, visibleBucketRange);
  }
}

function drawDistributionGrid(
  ctx: CanvasRenderingContext2D,
  chartWidth: number,
  chartHeight: number,
  yMax: number,
) {
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.font = "10px system-ui, sans-serif";

  for (let tickIndex = 0; tickIndex <= DIST_TICK_COUNT; tickIndex += 1) {
    const ratio = tickIndex / DIST_TICK_COUNT;
    const value = yMax * (1 - ratio);
    const y = DIST_CHART_TOP + chartHeight * ratio;

    ctx.fillStyle = "rgba(255, 245, 220, 0.08)";
    ctx.fillRect(DIST_CHART_LEFT, y - 0.5, chartWidth, 1);

    ctx.fillStyle = "rgba(212, 197, 173, 0.75)";
    ctx.fillText(`${percentFormatter.format(value)}%`, DIST_CHART_LEFT - 6, y);
  }
}

function drawDistributionBars(
  ctx: CanvasRenderingContext2D,
  chartWidth: number,
  chartHeight: number,
  selectedValues: number[],
  comparisonValues: number[] | null,
  yMax: number,
  visibleBucketRange: { start: number; end: number },
) {
  const visibleBucketCount = visibleBucketRange.end - visibleBucketRange.start + 1;
  const groupWidth = chartWidth / visibleBucketCount;
  const groupPadding = Math.min(8, groupWidth * 0.16);
  const innerGap = comparisonValues ? Math.min(4, groupWidth * 0.08) : 0;
  const usableWidth = Math.max(groupWidth - groupPadding * 2, 2);
  const barWidth = comparisonValues
    ? Math.max((usableWidth - innerGap) / 2, 1)
    : Math.max(usableWidth * 0.72, 1);

  for (let index = 0; index < PRICE_MENTION_BUCKETS.length; index += 1) {
    const groupX = groupXForBucket(index, chartWidth, visibleBucketRange) + groupPadding;
    if (groupX + usableWidth < DIST_CHART_LEFT || groupX > DIST_CHART_LEFT + chartWidth) {
      continue;
    }
    if (comparisonValues) {
      drawDistributionBar(
        ctx,
        groupX,
        chartHeight,
        barWidth,
        selectedValues[index],
        yMax,
        SELECTED_BAR_COLOR,
      );
      drawDistributionBar(
        ctx,
        groupX + barWidth + innerGap,
        chartHeight,
        barWidth,
        comparisonValues[index],
        yMax,
        COMPARISON_BAR_COLOR,
      );
    } else {
      drawDistributionBar(
        ctx,
        groupX + (usableWidth - barWidth) / 2,
        chartHeight,
        barWidth,
        selectedValues[index],
        yMax,
        SELECTED_BAR_COLOR,
      );
    }
  }
}

function drawDistributionBar(
  ctx: CanvasRenderingContext2D,
  x: number,
  chartHeight: number,
  width: number,
  value: number,
  yMax: number,
  fill: string,
) {
  const clampedValue = Math.max(0, value);
  const barHeight = yMax > 0 ? (clampedValue / yMax) * chartHeight : 0;
  const y = DIST_CHART_TOP + chartHeight - barHeight;
  const radius = Math.min(6, width / 2, barHeight / 2);

  ctx.fillStyle = fill;
  fillRoundedRect(ctx, x, y, width, barHeight, radius);
}

function drawDistributionXAxis(
  ctx: CanvasRenderingContext2D,
  chartWidth: number,
  chartHeight: number,
  visibleBucketRange: { start: number; end: number },
) {
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.font = "10px system-ui, sans-serif";
  ctx.fillStyle = "rgba(212, 197, 173, 0.78)";

  const visibleBucketCount = visibleBucketRange.end - visibleBucketRange.start + 1;
  const step = distributionLabelStep(Math.max(1, Math.ceil(visibleBucketCount)));
  const startIndex = Math.max(0, Math.floor(visibleBucketRange.start));
  const endIndex = Math.min(PRICE_MENTION_BUCKETS.length - 1, Math.ceil(visibleBucketRange.end));
  for (let index = startIndex; index <= endIndex; index += step) {
    const x = groupXForBucket(index, chartWidth, visibleBucketRange) + chartWidth / visibleBucketCount / 2;
    if (x < DIST_CHART_LEFT || x > DIST_CHART_LEFT + chartWidth) {
      continue;
    }
    const label = compactPriceFormatter.format(PRICE_MENTION_BUCKETS[index]);
    ctx.fillText(label, x, DIST_CHART_TOP + chartHeight + 8);
  }
}

function drawDistributionHover(
  ctx: CanvasRenderingContext2D,
  chartWidth: number,
  chartHeight: number,
  hoveredBucketIndex: number,
  visibleBucketRange: { start: number; end: number },
) {
  if (hoveredBucketIndex < 0 || hoveredBucketIndex >= PRICE_MENTION_BUCKETS.length) {
    return;
  }

  const visibleBucketCount = visibleBucketRange.end - visibleBucketRange.start + 1;
  const groupWidth = chartWidth / visibleBucketCount;
  const centerX = groupXForBucket(hoveredBucketIndex, chartWidth, visibleBucketRange) + groupWidth / 2;
  const label = hoverPriceFormatter.format(PRICE_MENTION_BUCKETS[hoveredBucketIndex]);
  const labelPaddingX = 10;
  const labelHeight = 28;

  ctx.save();
  ctx.strokeStyle = "rgba(255, 178, 64, 0.34)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(centerX, DIST_CHART_TOP);
  ctx.lineTo(centerX, DIST_CHART_TOP + chartHeight);
  ctx.stroke();
  ctx.restore();

  ctx.save();
  ctx.font = "11px system-ui, sans-serif";
  const textWidth = ctx.measureText(label).width;
  const labelWidth = textWidth + labelPaddingX * 2;
  const labelX = Math.max(
    DIST_CHART_LEFT,
    Math.min(centerX - labelWidth / 2, DIST_CHART_LEFT + chartWidth - labelWidth),
  );
  const labelY = DIST_CHART_TOP + chartHeight + 4;

  ctx.fillStyle = "#5c3a1e";
  fillRoundedRect(ctx, labelX, labelY, labelWidth, labelHeight, 8);
  ctx.fillStyle = "#f4ddbe";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, labelX + labelWidth / 2, labelY + labelHeight / 2 + 0.5);
  ctx.restore();
}

function fillRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  if (height <= 0 || width <= 0) {
    return;
  }

  if (radius <= 0) {
    ctx.fillRect(x, y, width, height);
    return;
  }

  ctx.beginPath();
  ctx.moveTo(x, y + height);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height);
  ctx.closePath();
  ctx.fill();
}

function roundUpDistributionMax(value: number): number {
  if (value <= 1) {
    return 1;
  }
  if (value <= 2) {
    return 2;
  }
  if (value <= 5) {
    return 5;
  }
  if (value <= 10) {
    return 10;
  }
  return Math.ceil(value / 5) * 5;
}

function distributionLabelStep(bucketCount: number): number {
  if (bucketCount <= 10) return 1;
  if (bucketCount <= 18) return 2;
  if (bucketCount <= 30) return 3;
  return 4;
}

function clampVisibleBucketRange(range: { start: number; end: number }): { start: number; end: number } {
  const maxIndex = PRICE_MENTION_BUCKETS.length - 1;
  const minVisibleCount = 3;
  const fullVisibleCount = PRICE_MENTION_BUCKETS.length;
  let visibleCount = range.end - range.start + 1;
  visibleCount = Math.max(minVisibleCount, Math.min(fullVisibleCount, visibleCount));

  let start = range.start;
  let end = start + visibleCount - 1;
  if (start < 0) {
    start = 0;
    end = visibleCount - 1;
  }
  if (end > maxIndex) {
    end = maxIndex;
    start = end - visibleCount + 1;
  }

  return {
    start: Math.max(0, start),
    end: Math.min(maxIndex, end),
  };
}

function zoomVisibleBucketRange(
  range: { start: number; end: number },
  zoomFactor: number,
  anchorRatio: number,
): { start: number; end: number } {
  const visibleCount = range.end - range.start + 1;
  const nextVisibleCount = visibleCount * zoomFactor;
  const anchorIndex = range.start + visibleCount * anchorRatio;
  const nextStart = anchorIndex - nextVisibleCount * anchorRatio;
  return clampVisibleBucketRange({
    start: nextStart,
    end: nextStart + nextVisibleCount - 1,
  });
}

function groupXForBucket(
  bucketIndex: number,
  chartWidth: number,
  visibleBucketRange: { start: number; end: number },
): number {
  const visibleBucketCount = visibleBucketRange.end - visibleBucketRange.start + 1;
  return DIST_CHART_LEFT + (bucketIndex - visibleBucketRange.start) * (chartWidth / visibleBucketCount);
}

function bucketIndexFromChartX(
  relativeX: number,
  chartWidth: number,
  visibleBucketRange: { start: number; end: number },
): number {
  const visibleBucketCount = visibleBucketRange.end - visibleBucketRange.start + 1;
  const bucketIndex = visibleBucketRange.start + (relativeX / chartWidth) * visibleBucketCount;
  return Math.max(
    0,
    Math.min(PRICE_MENTION_BUCKETS.length - 1, Math.floor(bucketIndex)),
  );
}
