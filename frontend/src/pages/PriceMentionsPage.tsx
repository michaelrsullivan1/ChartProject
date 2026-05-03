import { useEffect, useRef, useState } from "react";

import {
  fetchAggregateMoodCohorts,
  type AggregateMoodCohortsResponse,
} from "../api/authorOverview";
import { fetchPriceMentions, type PriceMentionsResponse } from "../api/priceMentions";
import { DashboardLoadingState } from "../components/DashboardLoadingState";

const API_BASE = "/api/views";
const ALL_COHORT_KEY = "__all__";

const LOG_MIN = Math.log10(10_000);
const LOG_MAX = Math.log10(10_000_000);
const DEFAULT_LOG_MAX = Math.log10(200_000);

const MENTION_TYPES = ["prediction", "conditional", "current", "historical", "unclassified"] as const;
type MentionTypeFilter = "all" | (typeof MENTION_TYPES)[number];

const priceFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 0,
});

const monthFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "2-digit",
  timeZone: "UTC",
});

const weekFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  timeZone: "UTC",
});

type CohortOption = { key: string; tagSlug: string | null; tagName: string };

type HeatmapViewState = {
  colStart: number;
  colEnd: number;
  logMin: number;
  logMax: number;
};

type HeatmapInteractionRegion = "plot" | "x-axis" | "y-axis" | "outside";

export function PriceMentionsPage() {
  const [data, setData] = useState<PriceMentionsResponse | null>(null);
  const [cohorts, setCohorts] = useState<CohortOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [granularity, setGranularity] = useState<"month" | "week">("week");
  const [mentionType, setMentionType] = useState<MentionTypeFilter>("all");
  const [includeLoConfidence, setIncludeLoConfidence] = useState(false);
  const [selectedCohortKey, setSelectedCohortKey] = useState<string>(ALL_COHORT_KEY);
  const [viewState, setViewState] = useState(() => createDefaultHeatmapViewState(undefined, "week"));

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const drawRef = useRef<(() => void) | null>(null);
  const dragStateRef = useRef<{ pointerId: number; lastClientX: number; lastClientY: number } | null>(null);

  const selectedCohortName =
    cohorts.find((c) => c.key === selectedCohortKey)?.tagName ?? "All tracked users";

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
    fetchPriceMentions(
      `${API_BASE}/price-mentions`,
      {
        granularity,
        cohortTag: cohortOpt?.tagSlug ?? null,
        minConfidence: includeLoConfidence ? 0.0 : 0.5,
        mentionType: mentionType === "all" ? null : mentionType,
      },
      ac.signal,
    )
      .then((res) => {
        setData(res);
        setIsLoading(false);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === "AbortError") return;
        setError(err instanceof Error ? err.message : "Failed to load data");
        setIsLoading(false);
      });

    return () => ac.abort();
  }, [granularity, mentionType, includeLoConfidence, selectedCohortKey, cohorts]);

  useEffect(() => {
    setViewState(createDefaultHeatmapViewState(data?.periods.length, granularity));
  }, [granularity, mentionType, includeLoConfidence, selectedCohortKey, data]);

  useEffect(() => {
    drawRef.current = () => {
      if (!canvasRef.current || !containerRef.current || !data) return;
      const canvas = canvasRef.current;
      const container = containerRef.current;
      const dpr = window.devicePixelRatio || 1;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.scale(dpr, dpr);
      drawHeatmap(ctx, w, h, data, viewState);
    };
    drawRef.current();
  }, [data, viewState]);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(() => drawRef.current?.());
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!containerRef.current || !data || isLoading || error || data.periods.length === 0) {
      return;
    }

    const container = containerRef.current;
    const heatmapData = data;

    function handlePointerDown(event: PointerEvent) {
      const rect = container.getBoundingClientRect();
      const localX = event.clientX - rect.left;
      const localY = event.clientY - rect.top;
      const chartW = rect.width - AXIS_LEFT - AXIS_RIGHT;
      const chartH = rect.height - AXIS_BOTTOM - AXIS_TOP;
      if (
        chartW <= 0 ||
        chartH <= 0 ||
        localX < AXIS_LEFT ||
        localX > AXIS_LEFT + chartW ||
        localY < AXIS_TOP ||
        localY > AXIS_TOP + chartH
      ) {
        return;
      }

      dragStateRef.current = {
        pointerId: event.pointerId,
        lastClientX: event.clientX,
        lastClientY: event.clientY,
      };
      container.setPointerCapture(event.pointerId);
    }

    function handlePointerMove(event: PointerEvent) {
      const dragState = dragStateRef.current;
      if (!dragState || dragState.pointerId !== event.pointerId) {
        return;
      }

      const rect = container.getBoundingClientRect();
      const chartW = rect.width - AXIS_LEFT - AXIS_RIGHT;
      const chartH = rect.height - AXIS_BOTTOM - AXIS_TOP;
      if (chartW <= 0 || chartH <= 0) {
        return;
      }

      dragStateRef.current = {
        pointerId: event.pointerId,
        lastClientX: event.clientX,
        lastClientY: event.clientY,
      };

      setViewState((currentView) =>
        clampHeatmapViewState(
          {
            colStart:
              currentView.colStart -
              ((event.clientX - dragState.lastClientX) / chartW) *
                (currentView.colEnd - currentView.colStart + 1),
            colEnd:
              currentView.colEnd -
              ((event.clientX - dragState.lastClientX) / chartW) *
                (currentView.colEnd - currentView.colStart + 1),
            logMin:
              currentView.logMin +
              ((event.clientY - dragState.lastClientY) / chartH) *
                (currentView.logMax - currentView.logMin),
            logMax:
              currentView.logMax +
              ((event.clientY - dragState.lastClientY) / chartH) *
                (currentView.logMax - currentView.logMin),
          },
          heatmapData.periods.length,
        ),
      );
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
      const localY = event.clientY - rect.top;
      const chartW = rect.width - AXIS_LEFT - AXIS_RIGHT;
      const chartH = rect.height - AXIS_BOTTOM - AXIS_TOP;
      if (chartW <= 0 || chartH <= 0) {
        return;
      }

      const region = resolveInteractionRegion(localX, localY, chartW, chartH);
      if (region === "outside") return;

      event.preventDefault();
      const zoomFactor =
        event.deltaY > 0 ? HEATMAP_WHEEL_ZOOM_FACTOR : 1 / HEATMAP_WHEEL_ZOOM_FACTOR;
      const anchorX = clampUnit((localX - AXIS_LEFT) / chartW);
      const anchorY = clampUnit((localY - AXIS_TOP) / chartH);
      setViewState((currentView) => {
        switch (region) {
          case "x-axis":
            return zoomHeatmapX(currentView, zoomFactor, anchorX, heatmapData.periods.length);
          case "y-axis":
            return zoomHeatmapY(currentView, zoomFactor, anchorY, heatmapData.periods.length);
          case "plot":
            return zoomHeatmapViewState(
              currentView,
              zoomFactor,
              anchorX,
              anchorY,
              heatmapData.periods.length,
            );
          default:
            return currentView;
        }
      });
    }

    function handleDoubleClick() {
      setViewState(
        createDefaultHeatmapViewState(
          heatmapData.periods.length,
          normalizeHeatmapGranularity(heatmapData.granularity),
        ),
      );
    }

    container.addEventListener("pointerdown", handlePointerDown);
    container.addEventListener("pointermove", handlePointerMove);
    container.addEventListener("pointerup", handlePointerUp);
    container.addEventListener("pointercancel", handlePointerUp);
    container.addEventListener("wheel", handleWheel, { passive: false });
    container.addEventListener("dblclick", handleDoubleClick);

    return () => {
      container.removeEventListener("pointerdown", handlePointerDown);
      container.removeEventListener("pointermove", handlePointerMove);
      container.removeEventListener("pointerup", handlePointerUp);
      container.removeEventListener("pointercancel", handlePointerUp);
      container.removeEventListener("wheel", handleWheel);
      container.removeEventListener("dblclick", handleDoubleClick);
    };
  }, [data, error, isLoading]);

  return (
    <section className="dashboard-page pm-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          <div>
            <p className="dashboard-eyebrow">Price Mentions — Heatmap</p>
            <p className="dashboard-subtitle">
              Bitcoin price levels mentioned by {selectedCohortName.toLowerCase()} — density over time
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
            <p className="chart-control-eyebrow">Granularity</p>
            <div className="pm-toggle-row">
              {(["month", "week"] as const).map((g) => (
                <button
                  key={g}
                  className={`chart-toggle-button${granularity === g ? " is-active" : ""}`}
                  onClick={() => setGranularity(g)}
                  type="button"
                >
                  {g.charAt(0).toUpperCase() + g.slice(1)}
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

        <div className="pm-chart-area" ref={containerRef}>
          {isLoading ? (
            <DashboardLoadingState />
          ) : error ? (
            <div className="pm-error">{error}</div>
          ) : data && data.periods.length === 0 ? (
            <div className="pm-empty">No price mentions found for the selected filters.</div>
          ) : (
            <canvas ref={canvasRef} className="pm-canvas" />
          )}
        </div>

        <div className="pm-legend">
          <span className="pm-legend-gradient" aria-hidden="true" />
          <span className="pm-legend-label">Low density</span>
          <span className="pm-legend-label pm-legend-label-high">High density</span>
          <span className="pm-legend-separator" />
          <span className="pm-legend-btc-line" aria-hidden="true" />
          <span className="pm-legend-label">BTC price</span>
          {data ? (
            <span className="pm-legend-meta">
              {data.periods.length} {data.granularity === "month" ? "months" : "weeks"}
            </span>
          ) : null}
          <span className="pm-legend-meta">Scroll to zoom, drag to pan, double-click to reset</span>
        </div>
      </article>
    </section>
  );
}

// ─── Canvas drawing ───────────────────────────────────────────────────────────

const AXIS_LEFT = 60;
const AXIS_BOTTOM = 28;
const AXIS_TOP = 6;
const AXIS_RIGHT = 8;
const HEATMAP_WHEEL_ZOOM_FACTOR = 1.04;
const HEATMAP_MIN_VISIBLE_COLS = 3;
const HEATMAP_MIN_LOG_SPAN = 0.18;

function drawHeatmap(
  ctx: CanvasRenderingContext2D,
  totalW: number,
  totalH: number,
  data: PriceMentionsResponse,
  viewState: HeatmapViewState,
) {
  const chartW = totalW - AXIS_LEFT - AXIS_RIGHT;
  const chartH = totalH - AXIS_BOTTOM - AXIS_TOP;
  if (chartW <= 0 || chartH <= 0) return;

  const { periods, bin_size: binSize } = data;
  if (periods.length === 0) return;
  const visibleColCount = viewState.colEnd - viewState.colStart + 1;
  const colW = chartW / visibleColCount;

  let maxCount = 1;
  const visibleStartIndex = Math.max(0, Math.floor(viewState.colStart));
  const visibleEndIndex = Math.min(periods.length - 1, Math.ceil(viewState.colEnd));
  for (let ci = visibleStartIndex; ci <= visibleEndIndex; ci += 1) {
    for (const mention of periods[ci].mentions) {
      if (isPriceRangeVisible(mention.price_usd, mention.price_usd + binSize, viewState)) {
        if (mention.count > maxCount) maxCount = mention.count;
      }
    }
  }

  ctx.clearRect(0, 0, totalW, totalH);
  ctx.fillStyle = "rgba(0,0,0,0.18)";
  ctx.fillRect(AXIS_LEFT, AXIS_TOP, chartW, chartH);

  for (let ci = visibleStartIndex; ci <= visibleEndIndex; ci += 1) {
    const px = AXIS_LEFT + (ci - viewState.colStart) * colW;
    for (const mention of periods[ci].mentions) {
      if (!isPriceRangeVisible(mention.price_usd, mention.price_usd + binSize, viewState)) {
        continue;
      }
      const y0 = priceToY(mention.price_usd, chartH, viewState) + AXIS_TOP;
      const y1 = priceToY(mention.price_usd + binSize, chartH, viewState) + AXIS_TOP;
      ctx.fillStyle = countToColor(mention.count, maxCount);
      ctx.fillRect(px, y0, colW + 0.5, Math.max(1, y1 - y0));
    }
  }

  drawBtcPriceLine(ctx, chartW, chartH, data, viewState);

  ctx.fillStyle = "rgba(180, 170, 160, 0.75)";
  ctx.font = "10px system-ui, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (const price of buildVisiblePriceTicks(viewState)) {
    const y = priceToY(price, chartH, viewState) + AXIS_TOP;
    if (y < AXIS_TOP || y > AXIS_TOP + chartH) continue;
    ctx.fillText(priceFormatter.format(price), AXIS_LEFT - 4, y);
    ctx.fillStyle = "rgba(180, 170, 160, 0.15)";
    ctx.fillRect(AXIS_LEFT, y - 0.5, chartW, 1);
    ctx.fillStyle = "rgba(180, 170, 160, 0.75)";
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.font = "10px system-ui, sans-serif";
  ctx.fillStyle = "rgba(180, 170, 160, 0.75)";
  const step = granularityLabelStep(Math.max(1, Math.ceil(visibleColCount)));
  for (let ci = visibleStartIndex; ci <= visibleEndIndex; ci += step) {
    const d = new Date(periods[ci].period_start);
    const label = formatHeatmapTimeLabel(d, data.granularity, visibleColCount);
    const x = AXIS_LEFT + (ci - viewState.colStart + 0.5) * colW;
    if (x < AXIS_LEFT || x > AXIS_LEFT + chartW) continue;
    ctx.fillText(label, x, AXIS_TOP + chartH + 4);
  }
}

function drawBtcPriceLine(
  ctx: CanvasRenderingContext2D,
  chartW: number,
  chartH: number,
  data: PriceMentionsResponse,
  viewState: HeatmapViewState,
) {
  const periods = data.periods;
  const visibleStartIndex = Math.max(0, Math.floor(viewState.colStart));
  const visibleEndIndex = Math.min(periods.length - 1, Math.ceil(viewState.colEnd));
  const visibleColCount = viewState.colEnd - viewState.colStart + 1;
  const colWidth = chartW / visibleColCount;
  const btcSeries = data.btc_series ?? [];

  ctx.save();
  ctx.strokeStyle = "rgba(255, 220, 60, 0.92)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  let firstPoint = true;

  if (btcSeries.length > 0) {
    const visibleStartDate = new Date(periods[visibleStartIndex].period_start);
    const visibleEndDate = periodEndDate(periods[visibleEndIndex].period_start, data.granularity);
    for (const point of btcSeries) {
      const observedAt = new Date(point.observed_at);
      if (
        observedAt < visibleStartDate ||
        observedAt > visibleEndDate ||
        !isPriceVisible(point.price, viewState)
      ) {
        continue;
      }

      const x =
        AXIS_LEFT +
        btcPointToChartX(observedAt, periods, data.granularity, viewState, colWidth);
      const y = priceToY(point.price, chartH, viewState) + AXIS_TOP;
      if (firstPoint) {
        ctx.moveTo(x, y);
        firstPoint = false;
      } else {
        ctx.lineTo(x, y);
      }
    }
  } else {
    for (let ci = visibleStartIndex; ci <= visibleEndIndex; ci += 1) {
      const btc = periods[ci].btc_close;
      if (btc == null || !isPriceVisible(btc, viewState)) continue;
      const x = AXIS_LEFT + (ci - viewState.colStart + 0.5) * colWidth;
      const y = priceToY(btc, chartH, viewState) + AXIS_TOP;
      if (firstPoint) {
        ctx.moveTo(x, y);
        firstPoint = false;
      } else {
        ctx.lineTo(x, y);
      }
    }
  }

  ctx.stroke();
  ctx.restore();
}

function priceToY(price: number, chartH: number, viewState: HeatmapViewState): number {
  const t =
    (Math.log10(Math.max(price, 1)) - viewState.logMin) /
    (viewState.logMax - viewState.logMin);
  return chartH * (1 - t);
}

function countToColor(count: number, maxCount: number): string {
  if (count <= 0) return "transparent";
  const t = Math.pow(count / maxCount, 0.45);
  let r: number, g: number, b: number, a: number;
  if (t < 0.25) {
    const s = t / 0.25;
    r = lerp(30, 40, s); g = lerp(60, 130, s); b = lerp(200, 240, s); a = lerp(0.35, 0.6, s);
  } else if (t < 0.55) {
    const s = (t - 0.25) / 0.3;
    r = lerp(40, 20, s); g = lerp(130, 180, s); b = lerp(240, 160, s); a = lerp(0.6, 0.75, s);
  } else if (t < 0.8) {
    const s = (t - 0.55) / 0.25;
    r = lerp(20, 245, s); g = lerp(180, 170, s); b = lerp(160, 20, s); a = lerp(0.75, 0.9, s);
  } else {
    const s = (t - 0.8) / 0.2;
    r = lerp(245, 255, s); g = lerp(170, 60, s); b = lerp(20, 20, s); a = lerp(0.9, 1.0, s);
  }
  return `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${a.toFixed(2)})`;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.max(0, Math.min(1, t));
}

function granularityLabelStep(numCols: number): number {
  if (numCols <= 10) return 1;
  if (numCols <= 20) return 2;
  if (numCols <= 36) return 3;
  if (numCols <= 72) return 6;
  if (numCols <= 156) return 13;
  return 26;
}

function createDefaultHeatmapViewState(
  periodCount = 1,
  granularity: "month" | "week" = "week",
): HeatmapViewState {
  const maxColIndex = Math.max(periodCount - 1, 0);
  const defaultVisibleCols = Math.max(1, Math.min(periodCount, defaultVisibleColumnCount(granularity)));
  const colEnd = maxColIndex;
  const colStart = Math.max(0, colEnd - defaultVisibleCols + 1);

  return {
    colStart,
    colEnd,
    logMin: LOG_MIN,
    logMax: DEFAULT_LOG_MAX,
  };
}

function defaultVisibleColumnCount(granularity: "month" | "week"): number {
  return granularity === "week" ? 52 : 12;
}

function normalizeHeatmapGranularity(granularity: string): "month" | "week" {
  return granularity === "month" ? "month" : "week";
}

function clampHeatmapViewState(viewState: HeatmapViewState, periodCount: number): HeatmapViewState {
  const maxColIndex = Math.max(periodCount - 1, 0);
  const fullColCount = Math.max(periodCount, 1);
  let visibleColCount = viewState.colEnd - viewState.colStart + 1;
  visibleColCount = Math.max(
    Math.min(HEATMAP_MIN_VISIBLE_COLS, fullColCount),
    Math.min(fullColCount, visibleColCount),
  );

  let colStart = viewState.colStart;
  let colEnd = colStart + visibleColCount - 1;
  if (colStart < 0) {
    colStart = 0;
    colEnd = visibleColCount - 1;
  }
  if (colEnd > maxColIndex) {
    colEnd = maxColIndex;
    colStart = colEnd - visibleColCount + 1;
  }
  if (periodCount <= 1) {
    colStart = 0;
    colEnd = maxColIndex;
  }

  let logSpan = viewState.logMax - viewState.logMin;
  logSpan = Math.max(HEATMAP_MIN_LOG_SPAN, Math.min(LOG_MAX - LOG_MIN, logSpan));
  let logMin = viewState.logMin;
  let logMax = logMin + logSpan;
  if (logMin < LOG_MIN) {
    logMin = LOG_MIN;
    logMax = logMin + logSpan;
  }
  if (logMax > LOG_MAX) {
    logMax = LOG_MAX;
    logMin = logMax - logSpan;
  }

  return { colStart, colEnd, logMin, logMax };
}

function zoomHeatmapViewState(
  viewState: HeatmapViewState,
  zoomFactor: number,
  anchorX: number,
  anchorY: number,
  periodCount: number,
): HeatmapViewState {
  return clampHeatmapViewState(
    {
      ...zoomHeatmapX(viewState, zoomFactor, anchorX, periodCount),
      ...zoomHeatmapY(viewState, zoomFactor, anchorY, periodCount),
    },
    periodCount,
  );
}

function zoomHeatmapX(
  viewState: HeatmapViewState,
  zoomFactor: number,
  anchorX: number,
  periodCount: number,
): HeatmapViewState {
  const visibleColCount = viewState.colEnd - viewState.colStart + 1;
  const nextVisibleColCount = visibleColCount * zoomFactor;
  const anchorCol = viewState.colStart + visibleColCount * anchorX;
  const nextColStart = anchorCol - nextVisibleColCount * anchorX;

  return clampHeatmapViewState(
    {
      colStart: nextColStart,
      colEnd: nextColStart + nextVisibleColCount - 1,
      logMin: viewState.logMin,
      logMax: viewState.logMax,
    },
    periodCount,
  );
}

function zoomHeatmapY(
  viewState: HeatmapViewState,
  zoomFactor: number,
  anchorY: number,
  periodCount: number,
): HeatmapViewState {
  const visibleLogSpan = viewState.logMax - viewState.logMin;
  const nextVisibleLogSpan = visibleLogSpan * zoomFactor;
  const anchorLog = viewState.logMax - visibleLogSpan * anchorY;
  const nextLogMax = anchorLog + nextVisibleLogSpan * anchorY;

  return clampHeatmapViewState(
    {
      colStart: viewState.colStart,
      colEnd: viewState.colEnd,
      logMin: nextLogMax - nextVisibleLogSpan,
      logMax: nextLogMax,
    },
    periodCount,
  );
}

function isPriceVisible(price: number, viewState: HeatmapViewState): boolean {
  const logPrice = Math.log10(Math.max(price, 1));
  return logPrice >= viewState.logMin && logPrice <= viewState.logMax;
}

function isPriceRangeVisible(minPrice: number, maxPrice: number, viewState: HeatmapViewState): boolean {
  const minLog = Math.log10(Math.max(minPrice, 1));
  const maxLog = Math.log10(Math.max(maxPrice, 1));
  return maxLog >= viewState.logMin && minLog <= viewState.logMax;
}

function btcPointToChartX(
  observedAt: Date,
  periods: PriceMentionsResponse["periods"],
  granularity: string,
  viewState: HeatmapViewState,
  colWidth: number,
): number {
  const bucketIndex = findBucketIndexForDate(observedAt, periods, granularity);
  if (bucketIndex < 0) {
    return 0;
  }

  const bucketStart = new Date(periods[bucketIndex].period_start);
  const bucketEnd = periodEndDate(periods[bucketIndex].period_start, granularity);
  const bucketDuration = Math.max(bucketEnd.getTime() - bucketStart.getTime(), 1);
  const offset = (observedAt.getTime() - bucketStart.getTime()) / bucketDuration;
  return (bucketIndex - viewState.colStart + Math.max(0, Math.min(1, offset))) * colWidth;
}

function findBucketIndexForDate(
  observedAt: Date,
  periods: PriceMentionsResponse["periods"],
  granularity: string,
): number {
  for (let index = 0; index < periods.length; index += 1) {
    const bucketStart = new Date(periods[index].period_start);
    const bucketEnd = periodEndDate(periods[index].period_start, granularity);
    if (observedAt >= bucketStart && observedAt <= bucketEnd) {
      return index;
    }
  }
  return -1;
}

function periodEndDate(periodStartIso: string, granularity: string): Date {
  const start = new Date(periodStartIso);
  if (granularity === "week") {
    return new Date(start.getTime() + 7 * 24 * 60 * 60 * 1000);
  }
  return new Date(Date.UTC(start.getUTCFullYear(), start.getUTCMonth() + 1, 1));
}

function resolveInteractionRegion(
  localX: number,
  localY: number,
  chartW: number,
  chartH: number,
): HeatmapInteractionRegion {
  const insidePlotX = localX >= AXIS_LEFT && localX <= AXIS_LEFT + chartW;
  const insidePlotY = localY >= AXIS_TOP && localY <= AXIS_TOP + chartH;
  if (insidePlotX && insidePlotY) return "plot";
  if (insidePlotX && localY > AXIS_TOP + chartH && localY <= AXIS_TOP + chartH + AXIS_BOTTOM) {
    return "x-axis";
  }
  if (insidePlotY && localX >= 0 && localX < AXIS_LEFT) {
    return "y-axis";
  }
  return "outside";
}

function clampUnit(value: number): number {
  return Math.max(0, Math.min(1, value));
}

function buildVisiblePriceTicks(viewState: HeatmapViewState): number[] {
  const visibleMin = Math.pow(10, viewState.logMin);
  const visibleMax = Math.pow(10, viewState.logMax);
  const baseTicks = buildPriceTickCandidates();
  const visibleTicks = baseTicks.filter((price) => price >= visibleMin && price <= visibleMax);
  if (visibleTicks.length <= 9) {
    return visibleTicks;
  }

  const step = Math.ceil(visibleTicks.length / 9);
  const reduced = visibleTicks.filter((_, index) => index % step === 0);
  const lastTick = visibleTicks[visibleTicks.length - 1];
  if (reduced[reduced.length - 1] !== lastTick) {
    reduced.push(lastTick);
  }
  return reduced;
}

function buildPriceTickCandidates(): number[] {
  const multipliers = [1, 2, 2.5, 5];
  const ticks: number[] = [];
  for (let power = 4; power <= 7; power += 1) {
    const base = 10 ** power;
    for (const multiplier of multipliers) {
      const value = base * multiplier;
      if (value >= 10_000 && value <= 10_000_000) {
        ticks.push(value);
      }
    }
  }
  return ticks;
}

function formatHeatmapTimeLabel(
  value: Date,
  granularity: string,
  visibleColCount: number,
): string {
  if (granularity === "week") {
    if (visibleColCount <= 12) {
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        year: "2-digit",
        timeZone: "UTC",
      }).format(value);
    }
    return weekFormatter.format(value);
  }

  if (visibleColCount <= 12) {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      year: "numeric",
      timeZone: "UTC",
    }).format(value);
  }
  return monthFormatter.format(value);
}
