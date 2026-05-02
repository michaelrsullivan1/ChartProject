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
import { DashboardLoadingState } from "../components/DashboardLoadingState";

const API_BASE = "/api/views";
const ALL_COHORT_KEY = "__all__";

const MENTION_TYPES = ["prediction", "conditional", "current", "historical", "unclassified"] as const;
type MentionTypeFilter = "all" | (typeof MENTION_TYPES)[number];

const PRICE_BUCKETS = [
  10_000, 20_000, 30_000, 40_000, 50_000, 60_000, 70_000, 80_000, 90_000, 100_000,
  125_000, 150_000, 175_000, 200_000, 250_000, 300_000, 400_000, 500_000,
  750_000, 1_000_000, 1_500_000, 2_000_000, 3_000_000, 5_000_000, 10_000_000,
];

const FAKE_EPOCH = 946684800;
const FAKE_DAY = 86400;

const compactPriceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 0,
});

type CohortOption = { key: string; tagSlug: string | null; tagName: string };

function bucketIndexToTime(index: number): UTCTimestamp {
  return (FAKE_EPOCH + index * FAKE_DAY) as UTCTimestamp;
}

function findBucketIndex(price: number): number {
  for (let i = PRICE_BUCKETS.length - 1; i >= 0; i--) {
    if (price >= PRICE_BUCKETS[i]) return i;
  }
  return -1;
}

function aggregateIntoBuckets(data: PriceMentionsResponse): number[] {
  const counts = new Array<number>(PRICE_BUCKETS.length).fill(0);
  for (const period of data.periods) {
    for (const mention of period.mentions) {
      const bi = findBucketIndex(mention.price_usd);
      if (bi >= 0) counts[bi] += mention.count;
    }
  }
  return counts;
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
  const [baselineData, setBaselineData] = useState<PriceMentionsResponse | null>(null);
  const [cohorts, setCohorts] = useState<CohortOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [mentionType, setMentionType] = useState<MentionTypeFilter>("all");
  const [includeLoConfidence, setIncludeLoConfidence] = useState(false);
  const [selectedCohortKey, setSelectedCohortKey] = useState<string>(ALL_COHORT_KEY);

  const containerRef = useRef<HTMLDivElement>(null);

  const selectedCohortName =
    cohorts.find((c) => c.key === selectedCohortKey)?.tagName ?? "All tracked users";
  const hasCohort = selectedCohortKey !== ALL_COHORT_KEY;

  useEffect(() => {
    const ac = new AbortController();
    fetchAggregateMoodCohorts(`${API_BASE}/aggregate-moods`, ac.signal)
      .then((res: AggregateMoodCohortsResponse) => {
        setCohorts([
          { key: ALL_COHORT_KEY, tagSlug: null, tagName: "All tracked users" },
          ...res.cohorts.map((c) => ({ key: c.tag_slug, tagSlug: c.tag_slug, tagName: c.tag_name })),
        ]);
      })
      .catch(() => {
        setCohorts([{ key: ALL_COHORT_KEY, tagSlug: null, tagName: "All tracked users" }]);
      });
    return () => ac.abort();
  }, []);

  useEffect(() => {
    const ac = new AbortController();
    setIsLoading(true);
    setError(null);

    const cohortOpt = cohorts.find((c) => c.key === selectedCohortKey);
    const params = {
      granularity: "month" as const,
      cohortTag: cohortOpt?.tagSlug ?? null,
      minConfidence: includeLoConfidence ? 0.0 : 0.5,
      mentionType: mentionType === "all" ? null : mentionType,
    };

    const baselinePromise = hasCohort
      ? fetchPriceMentions(`${API_BASE}/price-mentions`, { ...params, cohortTag: null }, ac.signal)
      : Promise.resolve(null);

    Promise.all([
      fetchPriceMentions(`${API_BASE}/price-mentions`, params, ac.signal),
      baselinePromise,
    ])
      .then(([primary, baseline]) => {
        setData(primary);
        setBaselineData(baseline);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load data");
        setIsLoading(false);
      });

    return () => ac.abort();
  }, [mentionType, includeLoConfidence, selectedCohortKey, cohorts, hasCohort]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !data) return;

    const cohortBuckets = aggregateIntoBuckets(data);
    const cohortTotal = cohortBuckets.reduce((s, c) => s + c, 0);

    const baselineBuckets = baselineData ? aggregateIntoBuckets(baselineData) : null;
    const baselineTotal = baselineBuckets ? baselineBuckets.reduce((s, c) => s + c, 0) : 0;

    const cohortSeries: LineData<Time>[] = PRICE_BUCKETS.map((_, i) => ({
      time: bucketIndexToTime(i) as Time,
      value: cohortTotal > 0 ? (cohortBuckets[i] / cohortTotal) * 100 : 0,
    }));

    const baselineSeries: LineData<Time>[] =
      baselineBuckets && baselineTotal > 0
        ? PRICE_BUCKETS.map((_, i) => ({
            time: bucketIndexToTime(i) as Time,
            value: (baselineBuckets[i] / baselineTotal) * 100,
          }))
        : [];

    const chart = createChart(container, {
      ...chartOptions,
      width: container.clientWidth,
      height: container.clientHeight,
    });

    if (baselineSeries.length > 0) {
      const baselineLine = chart.addSeries(LineSeries, {
        color: "rgba(198, 191, 180, 0.7)",
        lineWidth: 1,
        lineType: LineType.WithSteps,
        topColor: "rgba(198, 191, 180, 0.15)",
        bottomColor: "rgba(198, 191, 180, 0.02)",
        lastValueVisible: false,
        priceLineVisible: false,
        crosshairMarkerVisible: false,
        priceFormat: { type: "percent" as const },
      });
      baselineLine.setData(baselineSeries);
    }

    const cohortLine = chart.addSeries(LineSeries, {
      color: "rgba(100, 160, 255, 0.9)",
      lineWidth: 2,
      lineType: LineType.WithSteps,
      topColor: "rgba(100, 160, 255, 0.25)",
      bottomColor: "rgba(100, 160, 255, 0.02)",
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
  }, [data, baselineData]);

  const totalMentions = data
    ? data.periods.reduce((s, p) => s + p.mention_count, 0)
    : null;

  return (
    <section className="dashboard-page pm-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          <div>
            <p className="dashboard-eyebrow">Price Mentions — Distribution</p>
            <p className="dashboard-subtitle">
              {hasCohort
                ? `${selectedCohortName} vs. all tracked users — price level distribution`
                : "All tracked users — price level distribution"}
            </p>
          </div>
        </div>

        <div className="pm-controls">
          <div className="chart-control-card">
            <p className="chart-control-eyebrow">Cohort</p>
            <select
              className="pm-select"
              value={selectedCohortKey}
              onChange={(e) => setSelectedCohortKey(e.target.value)}
            >
              {cohorts.map((c) => (
                <option key={c.key} value={c.key}>{c.tagName}</option>
              ))}
            </select>
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

        <div className="pm-chart-area">
          {isLoading ? (
            <DashboardLoadingState />
          ) : error ? (
            <div className="pm-error">{error}</div>
          ) : data && data.periods.length === 0 ? (
            <div className="pm-empty">No price mentions found for the selected filters.</div>
          ) : (
            <div ref={containerRef} className="pm-lw-chart" />
          )}
        </div>

        <div className="pm-legend">
          {hasCohort ? (
            <>
              <span className="pm-legend-swatch pm-legend-swatch-cohort" aria-hidden="true" />
              <span className="pm-legend-label">{selectedCohortName}</span>
              <span className="pm-legend-swatch pm-legend-swatch-baseline" aria-hidden="true" />
              <span className="pm-legend-label">All tracked users</span>
            </>
          ) : (
            <>
              <span className="pm-legend-swatch pm-legend-swatch-cohort" aria-hidden="true" />
              <span className="pm-legend-label">All tracked users</span>
            </>
          )}
          {totalMentions !== null ? (
            <span className="pm-legend-meta">
              {totalMentions.toLocaleString()} total mentions
            </span>
          ) : null}
        </div>
      </article>
    </section>
  );
}
