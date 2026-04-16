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

type CohortSelectionKey = string;

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
  const [payload, setPayload] = useState<AggregateNarrativeResponse | null>(null);
  const [comparisonPayload, setComparisonPayload] = useState<AggregateNarrativeResponse | null>(
    null,
  );
  const [cohortPayload, setCohortPayload] = useState<AggregateNarrativeCohortsResponse | null>(null);
  const [selectedCohortKey, setSelectedCohortKey] = useState<CohortSelectionKey>(ALL_COHORT_KEY);
  const [pinnedCohortKey, setPinnedCohortKey] = useState<CohortSelectionKey | null>(null);
  const [selectedNarrativeSlug, setSelectedNarrativeSlug] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

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
      setSelectedNarrativeSlug(null);
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
                  <p className="metric-note">{selectedNarrative.phrase}</p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Selected Cohort</p>
                  <p className="metric-value">
                    {payload.cohort.selection.tag_name ?? "All tracked users"}
                  </p>
                  <p className="metric-note">
                    {integerFormatter.format(payload.cohort.user_count)} users in scope
                  </p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Total Matching Tweets</p>
                  <p className="metric-value">
                    {integerFormatter.format(selectedNarrative.summary.total_matching_tweets)}
                  </p>
                  <p className="metric-note">One count per tweet containing the phrase</p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Latest Weekly Count</p>
                  <p className="metric-value">
                    {integerFormatter.format(selectedNarrative.summary.latest_period_count)}
                  </p>
                  <p className="metric-note">
                    Week of {formatCompactDate(payload.range.end)}
                  </p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Peak Weekly Count</p>
                  <p className="metric-value">
                    {integerFormatter.format(selectedNarrative.summary.peak_period_count)}
                  </p>
                  <p className="metric-note">Highest weekly volume in selected range</p>
                </article>
                <article className="metric-card">
                  <p className="metric-label">Snapshot Refreshed</p>
                  <p className="metric-value">
                    {payload.generated_at ? formatCompactDate(payload.generated_at) : "Live"}
                  </p>
                  <p className="metric-note">
                    {payload.generated_at
                      ? timestampFormatter.format(new Date(payload.generated_at))
                      : "Built on demand"}
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
                    {payload.cohort.selection.tag_name ?? "All tracked users"} weekly volume
                  </span>
                  {comparisonNarrative && comparisonCohortOption ? (
                    <span className="chart-legend-item">
                      <span className="chart-swatch chart-swatch-narrative-comparison" />
                      {comparisonCohortOption.tagName} comparison line
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
  onSelectedCohortKeyChange: (value: CohortSelectionKey) => void;
  onPinnedCohortKeyToggle: (value: CohortSelectionKey) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const selectedSeries = useMemo<LineData<Time>[]>(
    () =>
      selectedNarrative.series.map((point) => ({
        time: toBusinessDay(point.period_start),
        value: point.matching_tweet_count,
      })),
    [selectedNarrative.series],
  );
  const comparisonSeries = useMemo<LineData<Time>[]>(
    () =>
      comparisonNarrative
        ? comparisonNarrative.series.map((point) => ({
            time: toBusinessDay(point.period_start),
            value: point.matching_tweet_count,
          }))
        : [],
    [comparisonNarrative],
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
    chart.timeScale().fitContent();

    function handleResize() {
      chart.applyOptions({
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
      });
      chart.timeScale().fitContent();
    }

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      comparisonLine = null;
      chart.remove();
    };
  }, [comparisonSeries, selectedSeries]);

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
            Viewing weekly volume for{" "}
            <strong>{payload.cohort.selection.tag_name ?? "All tracked users"}</strong>.
          </p>
          {comparisonCohortName ? (
            <p className="chart-control-note">
              Comparing against <strong>{comparisonCohortName}</strong>.
            </p>
          ) : null}
          <p className="chart-control-note">
            Snapshot: {generatedAt ? timestampFormatter.format(new Date(generatedAt)) : "Live"}
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

      <aside className="chart-sidebar">
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

function toBusinessDay(value: string): string {
  return value.slice(0, 10);
}

function formatCompactDate(value: string): string {
  return compactDateFormatter.format(new Date(value));
}
