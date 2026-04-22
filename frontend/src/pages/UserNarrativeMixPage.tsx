import { useEffect, useMemo, useRef, useState } from "react";
import {
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";

import {
  fetchPodcastNarrativeMix,
  type PodcastNarrativeMixPeriodRow,
  type PodcastNarrativeMixResponse,
} from "../api/podcastNarrativeMix";
import { DashboardLoadingState } from "../components/DashboardLoadingState";

const integerFormatter = new Intl.NumberFormat("en-US");
const percentFormatter = new Intl.NumberFormat("en-US", {
  style: "percent",
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});
const fullDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});
const timestampFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
  timeZone: "UTC",
});

const TOPIC_COLORS = [
  "#7af0b6",
  "#7dc6ff",
  "#f8ba5a",
  "#f38ba8",
  "#b0f07a",
  "#9d8cff",
  "#ff9b73",
  "#64e2cf",
  "#ffd26f",
  "#95b8ff",
  "#ff8fcf",
  "#9af5a2",
];

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
  leftPriceScale: { borderVisible: false },
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
    rightOffset: 3,
    barSpacing: 7.8,
    minBarSpacing: 0.25,
  },
};

type UserNarrativeMixPageProps = {
  personSlug: string;
};

type TimelineMode = "month" | "appearance_index";
type MetricMode = "share" | "count";

export function UserNarrativeMixPage({ personSlug }: UserNarrativeMixPageProps) {
  const [payload, setPayload] = useState<PodcastNarrativeMixResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timelineMode, setTimelineMode] = useState<TimelineMode>("appearance_index");
  const [metricMode, setMetricMode] = useState<MetricMode>("share");
  const [pinnedTopics, setPinnedTopics] = useState<string[]>([]);
  const [hoveredPeriodKey, setHoveredPeriodKey] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadView() {
      try {
        const response = await fetchPodcastNarrativeMix(personSlug, {
          signal: controller.signal,
        });
        setPayload(response);
        setError(null);
      } catch (loadError) {
        if (controller.signal.aborted) {
          return;
        }
        setPayload(null);
        setError(
          loadError instanceof Error
            ? loadError.message
            : "Unknown narrative mix fetch failure",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    setError(null);
    setPayload(null);
    void loadView();

    return () => {
      controller.abort();
    };
  }, [personSlug]);

  useEffect(() => {
    if (!payload) {
      return;
    }
    const initialTopics = payload.topics.slice(0, 5).map((row) => row.topic);
    setPinnedTopics(initialTopics);
  }, [payload]);

  const activePeriods = useMemo(
    () =>
      payload
        ? timelineMode === "month"
          ? payload.timeline_modes.month.periods
          : payload.timeline_modes.appearance_index.periods
        : [],
    [payload, timelineMode],
  );
  const topicRows = useMemo(() => (payload ? payload.topics : []), [payload]);
  const pinnedTopicSet = useMemo(() => new Set(pinnedTopics), [pinnedTopics]);
  const hoveredPeriod = useMemo(
    () => activePeriods.find((period) => period.period_key === hoveredPeriodKey) ?? null,
    [activePeriods, hoveredPeriodKey],
  );

  function togglePinnedTopic(topic: string) {
    setPinnedTopics((current) =>
      current.includes(topic)
        ? current.filter((value) => value !== topic)
        : [...current, topic],
    );
  }

  function resetPins() {
    setPinnedTopics(topicRows.slice(0, 8).map((row) => row.topic));
  }

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        {isLoading ? <DashboardLoadingState /> : null}
        {!isLoading && error ? <p className="status-copy">{error}</p> : null}
        {!isLoading && payload ? (
          <div className="content-stack">
            <div className="metric-strip metric-strip-dashboard">
              <article className="metric-card">
                <p className="metric-label">User</p>
                <p className="metric-value">{payload.subject.name}</p>
                <p className="metric-note">{payload.subject.slug}</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Appearances</p>
                <p className="metric-value">
                  {integerFormatter.format(payload.summary.appearance_count)}
                </p>
                <p className="metric-note">All dated appearances in imported corpus</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Beliefs</p>
                <p className="metric-value">
                  {integerFormatter.format(payload.summary.belief_count)}
                </p>
                <p className="metric-note">All dated beliefs</p>
              </article>
              <article className="metric-card">
                <p className="metric-label">Range</p>
                <p className="metric-value">
                  {formatDate(payload.summary.range_start)} - {formatDate(payload.summary.range_end)}
                </p>
                <p className="metric-note">Full history window</p>
              </article>
            </div>

            <article className="panel">
              <h2>Narrative Mix Chart</h2>
              <div className="tradingview-chart-shell">
                <aside className="chart-sidebar chart-sidebar-left">
                  <div className="chart-control-card">
                    <p className="chart-control-eyebrow">Timeline</p>
                    <div className="chart-toggle-group chart-toggle-group-vertical">
                      <button
                        className={`chart-toggle-button${timelineMode === "appearance_index" ? " is-active" : ""}`}
                        onClick={() => setTimelineMode("appearance_index")}
                        type="button"
                      >
                        Appearance Index
                      </button>
                      <button
                        className={`chart-toggle-button${timelineMode === "month" ? " is-active" : ""}`}
                        onClick={() => setTimelineMode("month")}
                        type="button"
                      >
                        Calendar Month
                      </button>
                    </div>
                  </div>
                  <div className="chart-control-card">
                    <p className="chart-control-eyebrow">Metric</p>
                    <div className="chart-toggle-group">
                      <button
                        className={`chart-toggle-button${metricMode === "share" ? " is-active" : ""}`}
                        onClick={() => setMetricMode("share")}
                        type="button"
                      >
                        Share %
                      </button>
                      <button
                        className={`chart-toggle-button${metricMode === "count" ? " is-active" : ""}`}
                        onClick={() => setMetricMode("count")}
                        type="button"
                      >
                        Raw Count
                      </button>
                    </div>
                  </div>
                  <div className="chart-control-card">
                    <p className="chart-control-eyebrow">Pinned Topics</p>
                    <p className="chart-control-note">
                      Use the topic table to pin any narratives you want to visualize.
                    </p>
                    <button
                      className="chart-toggle-button"
                      onClick={resetPins}
                      type="button"
                    >
                      Reset Pins
                    </button>
                  </div>
                </aside>

                <div className="chart-stage">
                  <NarrativeMixChart
                    metricMode={metricMode}
                    periods={activePeriods}
                    pinnedTopics={pinnedTopics}
                    timelineMode={timelineMode}
                    onHoverPeriodKeyChange={setHoveredPeriodKey}
                  />
                </div>

                <aside className="chart-sidebar">
                  <div className="chart-control-card">
                    <p className="chart-control-eyebrow">Method Notes</p>
                    <p className="chart-control-note">
                      Share mode uses labeled-topic beliefs as the denominator in each period.
                      Raw count mode uses direct topic belief counts.
                    </p>
                    <p className="chart-control-note">
                      Appearance Index mode uses one point per appearance on the x-axis (A1, A2,
                      A3...), without date labels on the axis.
                    </p>
                    {timelineMode === "appearance_index" && hoveredPeriod ? (
                      <p className="chart-control-note">
                        Hover: <strong>{hoveredPeriod.period_label}</strong>{" "}
                        {hoveredPeriod.show_name ? `· ${hoveredPeriod.show_name}` : ""}{" "}
                        {hoveredPeriod.period_start
                          ? `· ${formatDate(hoveredPeriod.period_start)}`
                          : ""}
                      </p>
                    ) : null}
                    <p className="chart-control-note">
                      Generated:{" "}
                      {payload.generated_at
                        ? timestampFormatter.format(new Date(payload.generated_at))
                        : "Unknown"}
                    </p>
                  </div>
                  <div className="chart-control-card">
                    <p className="chart-control-eyebrow">Pinned Topic Key</p>
                    {pinnedTopics.length === 0 ? (
                      <p className="chart-control-note">No pinned topics.</p>
                    ) : (
                      <div className="podcast-topic-legend-list">
                        {pinnedTopics.map((topic, index) => (
                          <button
                            className="podcast-topic-legend-item podcast-topic-legend-button"
                            key={topic}
                            onClick={() => togglePinnedTopic(topic)}
                            title={`Unpin ${topic}`}
                            type="button"
                          >
                            <span
                              aria-hidden="true"
                              className="podcast-topic-legend-swatch"
                              style={{ backgroundColor: TOPIC_COLORS[index % TOPIC_COLORS.length] }}
                            />
                            <span className="podcast-topic-legend-label">{topic}</span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </aside>
              </div>
            </article>

            <article className="panel">
              <h2>Topics</h2>
              <div className="bitcoin-table-shell podcast-topic-table-shell">
                <table className="bitcoin-table">
                  <thead>
                    <tr>
                      <th>Pin</th>
                      <th>Topic</th>
                      <th>Total Beliefs</th>
                      <th>Overall Share</th>
                      <th>First Seen</th>
                      <th>Last Seen</th>
                      <th>Active Periods</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topicRows.map((row) => {
                      const isPinned = pinnedTopicSet.has(row.topic);
                      return (
                        <tr key={row.topic} className={isPinned ? "is-active" : ""}>
                          <td>
                            <button
                              className={`chart-toggle-button${isPinned ? " is-active" : ""}`}
                              onClick={() => togglePinnedTopic(row.topic)}
                              type="button"
                            >
                              {isPinned ? "Pinned" : "Pin"}
                            </button>
                          </td>
                          <td>{row.topic}</td>
                          <td>{integerFormatter.format(row.total_beliefs)}</td>
                          <td>{percentFormatter.format(row.overall_share)}</td>
                          <td>{formatDate(row.first_seen)}</td>
                          <td>{formatDate(row.last_seen)}</td>
                          <td>
                            {integerFormatter.format(
                              timelineMode === "month"
                                ? row.active_month_count
                                : row.active_appearance_count,
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>

            <article className="panel">
              <h2>Periods</h2>
              <div className="bitcoin-table-shell">
                <table className="bitcoin-table">
                  <thead>
                    <tr>
                      <th>Period</th>
                      <th>Show</th>
                      <th>Episode</th>
                      <th>Appearances</th>
                      <th>Total Beliefs</th>
                      <th>Labeled Beliefs</th>
                      <th>Top Topic</th>
                      <th>Top Topic Share</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activePeriods.map((period) => {
                      const topTopic = period.topics[0];
                      return (
                        <tr key={period.period_key}>
                          <td>{period.period_label}</td>
                          <td>{period.show_name ?? "Multiple"}</td>
                          <td>{period.episode_title ?? "Multiple"}</td>
                          <td>{integerFormatter.format(period.appearance_count)}</td>
                          <td>{integerFormatter.format(period.total_beliefs)}</td>
                          <td>{integerFormatter.format(period.topic_labeled_beliefs)}</td>
                          <td>{topTopic ? topTopic.topic : "None"}</td>
                          <td>
                            {topTopic ? percentFormatter.format(topTopic.topic_share) : "0.0%"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </article>
          </div>
        ) : null}
      </article>
    </section>
  );
}

function NarrativeMixChart({
  periods,
  pinnedTopics,
  metricMode,
  timelineMode,
  onHoverPeriodKeyChange,
}: {
  periods: PodcastNarrativeMixPeriodRow[];
  pinnedTopics: string[];
  metricMode: MetricMode;
  timelineMode: TimelineMode;
  onHoverPeriodKeyChange: (periodKey: string | null) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || periods.length === 0) {
      return;
    }
    const chartContainer = container;

    const periodTime = new Map<string, UTCTimestamp>();
    const periodKeyByTime = new Map<number, string>();
    const periodLabelByTime = new Map<number, string>();
    for (const [index, period] of periods.entries()) {
      const time =
        timelineMode === "appearance_index"
          ? sequenceIndexToUtcTimestamp(index + 1)
          : period.period_start
            ? isoToUtcTimestamp(period.period_start)
            : sequenceIndexToUtcTimestamp(index + 1);
      periodTime.set(period.period_key, time);
      periodKeyByTime.set(time, period.period_key);
      periodLabelByTime.set(time, period.period_label);
    }

    const chart = createChart(chartContainer, {
      ...chartOptions,
      width: chartContainer.clientWidth,
      height: chartContainer.clientHeight,
      localization:
        timelineMode === "appearance_index"
          ? {
              timeFormatter: (time: Time) => {
                const timestamp = timeToTimestampSeconds(time);
                if (timestamp === null) {
                  return "";
                }
                return periodLabelByTime.get(timestamp) ?? "";
              },
            }
          : undefined,
      timeScale: {
        ...chartOptions.timeScale,
        tickMarkFormatter:
          timelineMode === "appearance_index"
            ? (time: Time) => {
                const timestamp = timeToTimestampSeconds(time);
                if (timestamp === null) {
                  return "";
                }
                return periodLabelByTime.get(timestamp) ?? "";
              }
            : undefined,
      },
    });

    chart.priceScale("right").applyOptions({
      autoScale: true,
      scaleMargins: { top: 0.12, bottom: 0.25 },
      minimumWidth: 72,
    });

    pinnedTopics.forEach((topic, index) => {
      const color = TOPIC_COLORS[index % TOPIC_COLORS.length];
      const series = chart.addSeries(LineSeries, {
        priceScaleId: "right",
        color,
        lineWidth: 2,
        lineType: LineType.Curved,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 3,
        crosshairMarkerBorderWidth: 1,
        crosshairMarkerBorderColor: color,
        crosshairMarkerBackgroundColor: "#17130f",
        lastValueVisible: false,
        priceLineVisible: false,
      });
      series.setData(
        periods.map((period) => {
          const topicRow = period.topics.find((row) => row.topic === topic);
          return {
            time: periodTime.get(period.period_key) as Time,
            value:
              metricMode === "share"
                ? (topicRow?.topic_share ?? 0) * 100
                : topicRow?.belief_count ?? 0,
          };
        }),
      );
    });

    function handleCrosshairMove(param: { time?: Time }) {
      if (param.time === undefined) {
        onHoverPeriodKeyChange(null);
        return;
      }
      const timestamp = timeToTimestampSeconds(param.time);
      onHoverPeriodKeyChange(timestamp !== null ? periodKeyByTime.get(timestamp) ?? null : null);
    }
    chart.subscribeCrosshairMove(handleCrosshairMove);

    chart.timeScale().fitContent();

    function handleResize() {
      chart.applyOptions({
        width: chartContainer.clientWidth,
        height: chartContainer.clientHeight,
      });
    }

    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      onHoverPeriodKeyChange(null);
      chart.remove();
    };
  }, [metricMode, onHoverPeriodKeyChange, periods, pinnedTopics, timelineMode]);

  if (periods.length === 0) {
    return <p className="status-copy">No period data is available.</p>;
  }

  return <div className="tradingview-chart" ref={containerRef} />;
}

function isoToUtcTimestamp(value: string): UTCTimestamp {
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
}

function sequenceIndexToUtcTimestamp(index: number): UTCTimestamp {
  const baseTimestampSeconds = Date.UTC(2018, 0, 1) / 1000;
  return Math.floor(baseTimestampSeconds + index * 86400) as UTCTimestamp;
}

function timeToTimestampSeconds(time: Time): number | null {
  if (typeof time === "number") {
    return time;
  }
  if (typeof time === "string") {
    return Math.floor(new Date(time).getTime() / 1000);
  }
  if (
    typeof time === "object" &&
    time !== null &&
    "year" in time &&
    "month" in time &&
    "day" in time
  ) {
    return Math.floor(Date.UTC(time.year, time.month - 1, time.day) / 1000);
  }
  return null;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Unknown";
  }
  return fullDateFormatter.format(new Date(value));
}
