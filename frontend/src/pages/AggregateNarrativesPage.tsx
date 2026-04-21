import { Pin } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type LineData,
  type Time,
} from "lightweight-charts";

import {
  fetchAggregateNarrativeCohorts,
  fetchAggregateNarratives,
  type AggregateNarrativeCohortsResponse,
  type AggregateNarrativeResponse,
} from "../api/aggregateNarratives";
import { ChartControlSelect } from "../components/ChartControlSelect";
import { DashboardLoadingState } from "../components/DashboardLoadingState";
import { CHART_WATERMARK_HANDLE } from "../lib/watermark";

const ALL_COHORT_KEY = "__all_tracked_users__";
const PRIMARY_LINE_COLOR = "#7af0b6";
const COMPARISON_LINE_COLOR = "rgba(198, 191, 180, 0.88)";
const DEFAULT_NARRATIVE_WINDOW_DAYS = 365;
const MS_PER_DAY = 24 * 60 * 60 * 1000;
const COHORT_QUERY_PARAM = "cohort";
const PINNED_QUERY_PARAM = "pinned";
const NARRATIVE_QUERY_PARAM = "narrative";

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

const integerFormatter = new Intl.NumberFormat("en-US");
const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
});
const compactDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});
const mentionRateFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  maximumFractionDigits: 2,
});

type CohortSelectionKey = string;
type NarrativeMetricMode = "raw_count" | "mention_rate" | "user_penetration";

type AggregateNarrativeCohortOption = {
  key: CohortSelectionKey;
  tagSlug: string | null;
  tagName: string;
  userCount: number | null;
};

type AggregateNarrativesPageProps = {
  showWatermark: boolean;
};

export function AggregateNarrativesPage({ showWatermark }: AggregateNarrativesPageProps) {
  const initialUrlState = useMemo(
    () => readAggregateNarrativesUrlState(window.location.hash),
    [],
  );
  const [payload, setPayload] = useState<AggregateNarrativeResponse | null>(null);
  const [comparisonPayload, setComparisonPayload] = useState<AggregateNarrativeResponse | null>(
    null,
  );
  const [cohortPayload, setCohortPayload] = useState<AggregateNarrativeCohortsResponse | null>(null);
  const [selectedCohortKey, setSelectedCohortKey] = useState<CohortSelectionKey>(
    initialUrlState.selectedCohortKey ?? ALL_COHORT_KEY,
  );
  const [pinnedCohortKey, setPinnedCohortKey] = useState<CohortSelectionKey | null>(
    initialUrlState.pinnedCohortKey ?? null,
  );
  const [selectedNarrativeSlug, setSelectedNarrativeSlug] = useState<string | null>(
    initialUrlState.selectedNarrativeSlug ?? null,
  );
  const [metricMode, setMetricMode] = useState<NarrativeMetricMode>("mention_rate");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    function handleHashChange() {
      const urlState = readAggregateNarrativesUrlState(window.location.hash);
      setSelectedCohortKey(urlState.selectedCohortKey ?? ALL_COHORT_KEY);
      setPinnedCohortKey(urlState.pinnedCohortKey ?? null);
      setSelectedNarrativeSlug(urlState.selectedNarrativeSlug ?? null);
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  useEffect(() => {
    const nextHash = buildAggregateNarrativesSelectionHash(
      selectedCohortKey,
      pinnedCohortKey,
      selectedNarrativeSlug,
    );
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  }, [pinnedCohortKey, selectedCohortKey, selectedNarrativeSlug]);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const cohortResponse = await fetchAggregateNarrativeCohorts();
        const cohortOptions = buildAggregateNarrativeCohortOptions(cohortResponse.cohorts);
        const effectiveSelectedCohortKey = isValidCohortKey(selectedCohortKey, cohortOptions)
          ? selectedCohortKey
          : ALL_COHORT_KEY;
        const effectivePinnedCohortKey =
          pinnedCohortKey !== null && isValidCohortKey(pinnedCohortKey, cohortOptions)
            ? pinnedCohortKey
            : null;
        const effectiveSelectedCohortTagSlug = cohortKeyToTagSlug(effectiveSelectedCohortKey);
        const effectiveComparisonCohortKey =
          effectivePinnedCohortKey !== null &&
          effectivePinnedCohortKey !== effectiveSelectedCohortKey
            ? effectivePinnedCohortKey
            : null;

        const [primaryPayload, comparisonResult] = await Promise.all([
          fetchAggregateNarratives(undefined, {
            cohortTagSlug: effectiveSelectedCohortTagSlug,
          }),
          effectiveComparisonCohortKey === null
            ? Promise.resolve(null)
            : fetchAggregateNarratives(undefined, {
                cohortTagSlug: cohortKeyToTagSlug(effectiveComparisonCohortKey),
              }),
        ]);

        if (cancelled) {
          return;
        }

        setPayload(primaryPayload);
        setComparisonPayload(comparisonResult);
        setCohortPayload(cohortResponse);
        if (selectedCohortKey !== effectiveSelectedCohortKey) {
          setSelectedCohortKey(effectiveSelectedCohortKey);
        }
        if (pinnedCohortKey !== effectivePinnedCohortKey) {
          setPinnedCohortKey(effectivePinnedCohortKey);
        }
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(
            loadError instanceof Error ? loadError.message : "Unknown aggregate narratives failure",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    setError(null);
    void loadView();

    return () => {
      cancelled = true;
    };
  }, [pinnedCohortKey, selectedCohortKey]);

  useEffect(() => {
    if (!payload) {
      return;
    }

    setSelectedNarrativeSlug((current) => {
      if (current && payload.narratives.some((narrative) => narrative.slug === current)) {
        return current;
      }
      return payload.default_narrative_slug ?? payload.narratives[0]?.slug ?? null;
    });
  }, [payload]);

  function handleSelectedCohortKeyChange(nextKey: CohortSelectionKey) {
    if (selectedCohortKey === nextKey) {
      return;
    }

    let nextPinnedCohortKey = pinnedCohortKey;
    if (pinnedCohortKey !== null) {
      if (pinnedCohortKey === selectedCohortKey) {
        nextPinnedCohortKey = pinnedCohortKey;
      } else if (pinnedCohortKey === nextKey) {
        nextPinnedCohortKey = null;
      } else {
        nextPinnedCohortKey = null;
      }
    }

    setSelectedCohortKey(nextKey);
    if (nextPinnedCohortKey !== pinnedCohortKey) {
      setPinnedCohortKey(nextPinnedCohortKey);
    }
  }

  function handlePinnedCohortKeyToggle(nextKey: CohortSelectionKey) {
    setPinnedCohortKey((currentKey) => (currentKey === nextKey ? null : nextKey));
  }

  const selectedNarrative = payload?.narratives.find(
    (narrative) => narrative.slug === selectedNarrativeSlug,
  ) ?? null;
  const comparisonNarrative =
    comparisonPayload?.narratives.find((narrative) => narrative.slug === selectedNarrativeSlug) ??
    null;
  const selectedTotalMentionRate = selectedNarrative
    ? resolveSummaryMentionRate(selectedNarrative.summary)
    : 0;
  const selectedLatestMentionRate = selectedNarrative
    ? resolveLatestMentionRate(selectedNarrative)
    : 0;
  const selectedPeakMentionRate = selectedNarrative
    ? resolvePeakMentionRate(selectedNarrative)
    : 0;
  const selectedTotalUserPenetrationRate = selectedNarrative
    ? resolveSummaryUserPenetrationRate(selectedNarrative.summary, payload?.cohort.user_count ?? 0)
    : 0;
  const selectedLatestUserPenetrationRate = selectedNarrative
    ? resolveLatestUserPenetrationRate(selectedNarrative, payload?.cohort.user_count ?? 0)
    : 0;
  const selectedPeakUserPenetrationRate = selectedNarrative
    ? resolvePeakUserPenetrationRate(selectedNarrative, payload?.cohort.user_count ?? 0)
    : 0;
  const cohortOptions = buildAggregateNarrativeCohortOptions(cohortPayload?.cohorts ?? []);
  const comparisonCohortOption =
    pinnedCohortKey === null
      ? null
      : cohortOptions.find((cohortOption) => cohortOption.key === pinnedCohortKey) ?? null;

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        {isLoading ? <DashboardLoadingState /> : null}
        {!payload ? !isLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null : null}
        {payload ? (
          payload.narratives.length === 0 ? (
            <div className="dashboard-workspace-header">
              <p className="status-copy">
                No managed narratives have been created yet. Add them in Global Settings to populate this page.
              </p>
            </div>
          ) : selectedNarrative ? (
            <>
              <div className="metric-strip metric-strip-dashboard">
                <article className="metric-card">
                  <p className="metric-label">Tracked Narrative</p>
                  <p className="metric-value">{selectedNarrative.name}</p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Selected Cohort</p>
                  <p className="metric-value">
                    {payload.cohort.selection.tag_name ?? "All tracked users"}
                  </p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">
                    {metricMode === "mention_rate"
                      ? "Overall Mention Rate"
                      : metricMode === "user_penetration"
                        ? "Overall User Penetration"
                        : "Total Matching Tweets"}
                  </p>
                  <p className="metric-value">
                    {metricMode === "mention_rate"
                      ? formatMentionRate(selectedTotalMentionRate)
                      : metricMode === "user_penetration"
                        ? formatMentionRate(selectedTotalUserPenetrationRate)
                        : integerFormatter.format(selectedNarrative.summary.total_matching_tweets)}
                  </p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">
                    {metricMode === "mention_rate"
                      ? "Latest Weekly Mention Rate"
                      : metricMode === "user_penetration"
                        ? "Latest Weekly User Penetration"
                        : "Latest Weekly Count"}
                  </p>
                  <p className="metric-value">
                    {metricMode === "mention_rate"
                      ? formatMentionRate(selectedLatestMentionRate)
                      : metricMode === "user_penetration"
                        ? formatMentionRate(selectedLatestUserPenetrationRate)
                        : integerFormatter.format(selectedNarrative.summary.latest_period_count)}
                  </p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">
                    {metricMode === "mention_rate"
                      ? "Peak Weekly Mention Rate"
                      : metricMode === "user_penetration"
                        ? "Peak Weekly User Penetration"
                        : "Peak Weekly Count"}
                  </p>
                  <p className="metric-value">
                    {metricMode === "mention_rate"
                      ? formatMentionRate(selectedPeakMentionRate)
                      : metricMode === "user_penetration"
                        ? formatMentionRate(selectedPeakUserPenetrationRate)
                        : integerFormatter.format(selectedNarrative.summary.peak_period_count)}
                  </p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Snapshot Refreshed</p>
                  <p className="metric-value">
                    {payload.generated_at ? formatCompactDate(payload.generated_at) : "Live"}
                  </p>
                </article>
              </div>

              <div className="chart-shell chart-shell-dashboard">
                <AggregateNarrativeHistoryChart
                  comparisonCohortName={comparisonCohortOption?.tagName ?? null}
                  comparisonNarrative={comparisonNarrative}
                  cohortOptions={cohortOptions}
                  generatedAt={payload.generated_at ?? null}
                  onPinnedCohortKeyToggle={handlePinnedCohortKeyToggle}
                  onSelectedCohortKeyChange={handleSelectedCohortKeyChange}
                  onSelectedNarrativeSlugChange={setSelectedNarrativeSlug}
                  metricMode={metricMode}
                  onMetricModeChange={setMetricMode}
                  payload={payload}
                  pinnedCohortKey={pinnedCohortKey}
                  selectedCohortKey={selectedCohortKey}
                  selectedNarrative={selectedNarrative}
                  selectedNarrativeSlug={selectedNarrativeSlug}
                  showWatermark={showWatermark}
                />
              </div>

              <div className="chart-caption-row chart-caption-row-dashboard">
                <div className="chart-legend" aria-label="Chart legend">
                  <span className="chart-legend-item">
                    <span className="chart-swatch chart-swatch-narrative-primary" />
                    {payload.cohort.selection.tag_name ?? "All tracked users"}{" "}
                    {metricMode === "mention_rate"
                      ? "weekly mention rate"
                      : metricMode === "user_penetration"
                        ? "weekly user penetration"
                        : "weekly matching tweets"}
                  </span>
                  {comparisonNarrative && comparisonCohortOption ? (
                    <span className="chart-legend-item">
                      <span className="chart-swatch chart-swatch-narrative-comparison" />
                      {comparisonCohortOption.tagName}{" "}
                      {metricMode === "mention_rate"
                        ? "mention-rate comparison"
                        : metricMode === "user_penetration"
                          ? "user-penetration comparison"
                          : "count comparison"}
                    </span>
                  ) : null}
                </div>
              </div>
            </>
          ) : null
        ) : null}
      </article>
    </section>
  );
}

function AggregateNarrativeHistoryChart({
  payload,
  selectedNarrative,
  comparisonNarrative,
  selectedNarrativeSlug,
  onSelectedNarrativeSlugChange,
  showWatermark,
  generatedAt,
  cohortOptions,
  selectedCohortKey,
  pinnedCohortKey,
  comparisonCohortName,
  metricMode,
  onMetricModeChange,
  onSelectedCohortKeyChange,
  onPinnedCohortKeyToggle,
}: {
  payload: AggregateNarrativeResponse;
  selectedNarrative: AggregateNarrativeResponse["narratives"][number];
  comparisonNarrative: AggregateNarrativeResponse["narratives"][number] | null;
  selectedNarrativeSlug: string | null;
  onSelectedNarrativeSlugChange: (value: string) => void;
  showWatermark: boolean;
  generatedAt: string | null;
  cohortOptions: AggregateNarrativeCohortOption[];
  selectedCohortKey: CohortSelectionKey;
  pinnedCohortKey: CohortSelectionKey | null;
  comparisonCohortName: string | null;
  metricMode: NarrativeMetricMode;
  onMetricModeChange: (value: NarrativeMetricMode) => void;
  onSelectedCohortKeyChange: (value: CohortSelectionKey) => void;
  onPinnedCohortKeyToggle: (value: CohortSelectionKey) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const selectedSeries = useMemo<LineData<Time>[]>(
    () =>
      selectedNarrative.series.map((point) => ({
        time: toBusinessDay(point.period_start),
        value:
          metricMode === "mention_rate"
            ? resolveSeriesMentionRate(point) * 100
            : metricMode === "user_penetration"
              ? resolveSeriesUserPenetrationRate(point, payload.cohort.user_count) * 100
              : point.matching_tweet_count,
      })),
    [metricMode, payload.cohort.user_count, selectedNarrative.series],
  );
  const comparisonSeries = useMemo<LineData<Time>[]>(
    () =>
      comparisonNarrative
        ? comparisonNarrative.series.map((point) => ({
            time: toBusinessDay(point.period_start),
            value:
              metricMode === "mention_rate"
                ? resolveSeriesMentionRate(point) * 100
                : metricMode === "user_penetration"
                  ? resolveSeriesUserPenetrationRate(point, payload.cohort.user_count) * 100
                  : point.matching_tweet_count,
          }))
        : [],
    [comparisonNarrative, metricMode, payload.cohort.user_count],
  );
  const defaultVisibleRange = useMemo(
    () =>
      buildRecentTimeVisibleRange(
        selectedNarrative.series.map((point) => point.period_start),
        DEFAULT_NARRATIVE_WINDOW_DAYS,
      ),
    [selectedNarrative.series],
  );
  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const chartContainer = container;

    const chart = createChart(chartContainer, {
      ...chartOptions,
      width: chartContainer.clientWidth,
      height: chartContainer.clientHeight,
    });

    const primarySeries = chart.addSeries(LineSeries, {
      color: PRIMARY_LINE_COLOR,
      lineWidth: 3,
      lineType: LineType.Curved,
      crosshairMarkerVisible: true,
      crosshairMarkerRadius: 5,
      crosshairMarkerBorderWidth: 2,
      crosshairMarkerBorderColor: PRIMARY_LINE_COLOR,
      crosshairMarkerBackgroundColor: "#17130f",
      lastValueVisible: false,
      priceLineVisible: false,
    });
    primarySeries.setData(selectedSeries);

    let comparisonLine = null;
    if (comparisonSeries.length > 0) {
      comparisonLine = chart.addSeries(LineSeries, {
        color: COMPARISON_LINE_COLOR,
        lineWidth: 2,
        lineType: LineType.Curved,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      comparisonLine.setData(comparisonSeries);
    }

    chart.priceScale("right").applyOptions({
      autoScale: true,
      scaleMargins: { top: 0.12, bottom: 0.18 },
      minimumWidth: 72,
    });
    if (defaultVisibleRange) {
      chart.timeScale().setVisibleRange(defaultVisibleRange);
    } else {
      chart.timeScale().fitContent();
    }

    function handleResize() {
      chart.applyOptions({
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
      });
    }

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      comparisonLine = null;
      chart.remove();
    };
  }, [comparisonSeries, defaultVisibleRange, selectedSeries]);

  return (
    <div className="tradingview-chart-shell">
      <aside className="chart-sidebar chart-sidebar-left">
        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Narrative</p>
          <label className="chart-control-field">
            <span className="sr-only">Managed narrative</span>
            <ChartControlSelect
              ariaLabel="Managed narrative"
              onChange={onSelectedNarrativeSlugChange}
              options={payload.narratives.map((narrative) => ({
                value: narrative.slug,
                label: narrative.name,
              }))}
              value={selectedNarrativeSlug ?? payload.default_narrative_slug ?? ""}
            />
          </label>
          <p className="chart-control-note">
            Phrase: <strong>{selectedNarrative.phrase}</strong>
          </p>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Selection</p>
          <p className="chart-control-note">
            Viewing weekly{" "}
            {metricMode === "mention_rate"
              ? "mention rate"
              : metricMode === "user_penetration"
                ? "user penetration"
                : "matching tweet volume"}{" "}
            for{" "}
            <strong>{payload.cohort.selection.tag_name ?? "All tracked users"}</strong>.
          </p>
          {comparisonCohortName ? (
            <p className="chart-control-note">
              Comparing against <strong>{comparisonCohortName}</strong> with{" "}
              {metricMode === "mention_rate" || metricMode === "user_penetration"
                ? "rate-normalized values"
                : "raw counts"}.
            </p>
          ) : null}
          <p className="chart-control-note">
            Snapshot: {generatedAt ? timestampFormatter.format(new Date(generatedAt)) : "Live"}
          </p>
        </div>

        <div className="chart-control-card">
          <p className="chart-control-eyebrow">Metric</p>
          <div className="chart-toggle-group chart-toggle-group-vertical">
            <button
              className={`chart-toggle-button${metricMode === "mention_rate" ? " is-active" : ""}`}
              onClick={() => onMetricModeChange("mention_rate")}
              type="button"
            >
              Mention Rate
            </button>
            <button
              className={`chart-toggle-button${metricMode === "raw_count" ? " is-active" : ""}`}
              onClick={() => onMetricModeChange("raw_count")}
              type="button"
            >
              Raw Count
            </button>
            <button
              className={`chart-toggle-button${metricMode === "user_penetration" ? " is-active" : ""}`}
              onClick={() => onMetricModeChange("user_penetration")}
              type="button"
            >
              User Penetration
            </button>
          </div>
          <p className="chart-control-note">
            This toggle applies to both the selected cohort and any pinned cohort comparison.
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

      <aside className="chart-sidebar chart-sidebar-cohorts-only">
        <div className="chart-control-card">
          <p className="chart-control-eyebrow">User Cohorts</p>
          <div className="chart-cohort-list" role="group" aria-label="User cohorts">
            {cohortOptions.map((cohortOption) => {
              const isSelected = selectedCohortKey === cohortOption.key;
              const isPinned = pinnedCohortKey === cohortOption.key;

              return (
                <div className="chart-cohort-row" key={cohortOption.key}>
                  <button
                    className={`chart-toggle-button chart-cohort-select-button${isSelected ? " is-active" : ""}`}
                    onClick={() => onSelectedCohortKeyChange(cohortOption.key)}
                    type="button"
                  >
                    {cohortOption.tagName}
                  </button>
                  <button
                    aria-label={`${isPinned ? "Unpin" : "Pin"} ${cohortOption.tagName}`}
                    aria-pressed={isPinned}
                    className={`chart-toggle-button chart-pin-button${isPinned ? " is-active" : ""}`}
                    onClick={() => onPinnedCohortKeyToggle(cohortOption.key)}
                    title={isPinned ? "Unpin cohort" : "Pin cohort"}
                    type="button"
                  >
                    <Pin aria-hidden="true" className="chart-pin-icon" size={16} strokeWidth={1.9} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </aside>
    </div>
  );
}

function buildAggregateNarrativeCohortOptions(
  cohorts: AggregateNarrativeCohortsResponse["cohorts"],
): AggregateNarrativeCohortOption[] {
  return [
    {
      key: ALL_COHORT_KEY,
      tagSlug: null,
      tagName: "All tracked users",
      userCount: null,
    },
    ...cohorts.map((cohort) => ({
      key: cohort.tag_slug,
      tagSlug: cohort.tag_slug,
      tagName: cohort.tag_name,
      userCount: cohort.user_count,
    })),
  ];
}

function isValidCohortKey(
  value: CohortSelectionKey,
  cohortOptions: AggregateNarrativeCohortOption[],
): boolean {
  return cohortOptions.some((cohortOption) => cohortOption.key === value);
}

function cohortKeyToTagSlug(value: CohortSelectionKey): string | null {
  return value === ALL_COHORT_KEY ? null : value;
}

function buildAggregateNarrativesSelectionHash(
  selectedCohortKey: CohortSelectionKey,
  pinnedCohortKey: CohortSelectionKey | null,
  selectedNarrativeSlug: string | null,
): string {
  const query = new URLSearchParams();
  query.set(COHORT_QUERY_PARAM, selectedCohortKey);
  if (pinnedCohortKey !== null) {
    query.set(PINNED_QUERY_PARAM, pinnedCohortKey);
  }
  if (selectedNarrativeSlug !== null) {
    query.set(NARRATIVE_QUERY_PARAM, selectedNarrativeSlug);
  }

  const serializedQuery = query.toString();
  return `#/aggregate-narratives${serializedQuery ? `?${serializedQuery}` : ""}`;
}

function readAggregateNarrativesUrlState(hash: string): {
  selectedCohortKey: CohortSelectionKey | null;
  pinnedCohortKey: CohortSelectionKey | null;
  selectedNarrativeSlug: string | null;
} {
  const normalizedHash = hash.startsWith("#") ? hash.slice(1) : hash;
  const queryIndex = normalizedHash.indexOf("?");
  const path = queryIndex >= 0 ? normalizedHash.slice(0, queryIndex) : normalizedHash;
  if (path !== "/aggregate-narratives") {
    return {
      selectedCohortKey: null,
      pinnedCohortKey: null,
      selectedNarrativeSlug: null,
    };
  }

  const queryString = queryIndex >= 0 ? normalizedHash.slice(queryIndex + 1) : "";
  const params = new URLSearchParams(queryString);
  const selectedCohortKey = normalizeOptionalQueryParam(params.get(COHORT_QUERY_PARAM));
  const pinnedCohortKey = normalizeOptionalQueryParam(params.get(PINNED_QUERY_PARAM));
  const selectedNarrativeSlug = normalizeOptionalQueryParam(params.get(NARRATIVE_QUERY_PARAM));

  return {
    selectedCohortKey,
    pinnedCohortKey,
    selectedNarrativeSlug,
  };
}

function normalizeOptionalQueryParam(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

function toBusinessDay(value: string): string {
  return value.slice(0, 10);
}

function buildRecentTimeVisibleRange(
  isoTimestamps: string[],
  windowDays: number,
): { from: Time; to: Time } | null {
  if (isoTimestamps.length === 0) {
    return null;
  }

  const epochTimes = isoTimestamps
    .map((timestamp) => Date.parse(timestamp))
    .filter((epoch): epoch is number => Number.isFinite(epoch));
  if (epochTimes.length === 0) {
    return null;
  }

  const latestTime = Math.max(...epochTimes);
  const earliestTime = Math.min(...epochTimes);
  const rangeStart = Math.max(earliestTime, latestTime - windowDays * MS_PER_DAY);
  return {
    from: toBusinessDay(new Date(rangeStart).toISOString()),
    to: toBusinessDay(new Date(latestTime).toISOString()),
  };
}

function formatCompactDate(value: string): string {
  return compactDateFormatter.format(new Date(value));
}

function formatMentionRate(value: number): string {
  return mentionRateFormatter.format(value);
}

function resolveSummaryMentionRate(
  summary: AggregateNarrativeResponse["narratives"][number]["summary"],
): number {
  if (typeof summary.total_mention_rate === "number") {
    return summary.total_mention_rate;
  }
  return safeRate(summary.total_matching_tweets, summary.total_tweet_count ?? 0);
}

function resolveLatestMentionRate(
  narrative: AggregateNarrativeResponse["narratives"][number],
): number {
  if (typeof narrative.summary.latest_period_mention_rate === "number") {
    return narrative.summary.latest_period_mention_rate;
  }
  return safeRate(
    narrative.summary.latest_period_count,
    narrative.summary.latest_period_total_tweets ??
      narrative.series[narrative.series.length - 1]?.total_tweet_count ??
      0,
  );
}

function resolvePeakMentionRate(
  narrative: AggregateNarrativeResponse["narratives"][number],
): number {
  if (typeof narrative.summary.peak_period_mention_rate === "number") {
    return narrative.summary.peak_period_mention_rate;
  }
  if (narrative.series.length === 0) {
    return 0;
  }
  return narrative.series.reduce((peak, point) => Math.max(peak, resolveSeriesMentionRate(point)), 0);
}

function resolveSummaryUserPenetrationRate(
  summary: AggregateNarrativeResponse["narratives"][number]["summary"],
  cohortUserCount: number,
): number {
  if (typeof summary.total_user_penetration_rate === "number") {
    return summary.total_user_penetration_rate;
  }
  return safeRate(summary.total_matching_users ?? 0, summary.total_user_count ?? cohortUserCount);
}

function resolveLatestUserPenetrationRate(
  narrative: AggregateNarrativeResponse["narratives"][number],
  cohortUserCount: number,
): number {
  if (typeof narrative.summary.latest_period_user_penetration_rate === "number") {
    return narrative.summary.latest_period_user_penetration_rate;
  }
  return safeRate(
    narrative.summary.latest_period_matching_users ??
      narrative.series[narrative.series.length - 1]?.matching_user_count ??
      0,
    cohortUserCount,
  );
}

function resolvePeakUserPenetrationRate(
  narrative: AggregateNarrativeResponse["narratives"][number],
  cohortUserCount: number,
): number {
  if (typeof narrative.summary.peak_period_user_penetration_rate === "number") {
    return narrative.summary.peak_period_user_penetration_rate;
  }
  if (narrative.series.length === 0) {
    return 0;
  }
  return narrative.series.reduce(
    (peak, point) => Math.max(peak, resolveSeriesUserPenetrationRate(point, cohortUserCount)),
    0,
  );
}

function resolveSeriesMentionRate(
  point: AggregateNarrativeResponse["narratives"][number]["series"][number],
): number {
  if (typeof point.mention_rate === "number") {
    return point.mention_rate;
  }
  return safeRate(point.matching_tweet_count, point.total_tweet_count ?? 0);
}

function resolveSeriesUserPenetrationRate(
  point: AggregateNarrativeResponse["narratives"][number]["series"][number],
  cohortUserCount: number,
): number {
  if (typeof point.user_penetration_rate === "number") {
    return point.user_penetration_rate;
  }
  return safeRate(point.matching_user_count ?? 0, cohortUserCount);
}

function safeRate(numerator: number, denominator: number): number {
  if (denominator <= 0) {
    return 0;
  }
  return numerator / denominator;
}
