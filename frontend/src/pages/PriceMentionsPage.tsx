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

export function PriceMentionsPage() {
  const [data, setData] = useState<PriceMentionsResponse | null>(null);
  const [cohorts, setCohorts] = useState<CohortOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [granularity, setGranularity] = useState<"month" | "week">("month");
  const [mentionType, setMentionType] = useState<MentionTypeFilter>("all");
  const [includeLoConfidence, setIncludeLoConfidence] = useState(false);
  const [selectedCohortKey, setSelectedCohortKey] = useState<string>(ALL_COHORT_KEY);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Load cohorts once
  useEffect(() => {
    const ac = new AbortController();
    fetchAggregateMoodCohorts(`${API_BASE}/aggregate-moods`, ac.signal)
      .then((res: AggregateMoodCohortsResponse) => {
        const opts: CohortOption[] = [
          { key: ALL_COHORT_KEY, tagSlug: null, tagName: "All tracked users" },
          ...res.cohorts.map((c) => ({ key: c.tag_slug, tagSlug: c.tag_slug, tagName: c.tag_name })),
        ];
        setCohorts(opts);
      })
      .catch(() => {
        setCohorts([{ key: ALL_COHORT_KEY, tagSlug: null, tagName: "All tracked users" }]);
      });
    return () => ac.abort();
  }, []);

  // Load price mention data whenever controls change
  useEffect(() => {
    const ac = new AbortController();
    setIsLoading(true);
    setError(null);

    const cohortOpt = cohorts.find((c) => c.key === selectedCohortKey);
    const tagSlug = cohortOpt?.tagSlug ?? null;

    fetchPriceMentions(
      `${API_BASE}/price-mentions`,
      {
        granularity,
        cohortTag: tagSlug,
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

  // Draw heatmap whenever data or canvas size changes
  useEffect(() => {
    if (!data || !canvasRef.current || !containerRef.current) return;

    const canvas = canvasRef.current;
    const container = containerRef.current;
    const dpr = window.devicePixelRatio || 1;

    const containerW = container.clientWidth;
    const containerH = container.clientHeight;
    canvas.width = containerW * dpr;
    canvas.height = containerH * dpr;
    canvas.style.width = `${containerW}px`;
    canvas.style.height = `${containerH}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.scale(dpr, dpr);

    drawHeatmap(ctx, containerW, containerH, data);
  }, [data]);

  // Redraw on resize
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver(() => {
      if (!data || !canvasRef.current || !containerRef.current) return;
      const canvas = canvasRef.current;
      const container = containerRef.current;
      const dpr = window.devicePixelRatio || 1;
      const w = container.clientWidth;
      const h = container.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.scale(dpr, dpr);
      drawHeatmap(ctx, w, h, data);
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [data]);

  const selectedCohortName =
    cohorts.find((c) => c.key === selectedCohortKey)?.tagName ?? "All tracked users";

  return (
    <section className="dashboard-page pm-page">
      <article className="panel panel-accent dashboard-workspace">
        <div className="dashboard-workspace-header">
          <div>
            <p className="dashboard-eyebrow">Price Mentions</p>
            <p className="dashboard-subtitle">
              Bitcoin price levels mentioned by {selectedCohortName.toLowerCase()} — density heatmap
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
                <option key={c.key} value={c.key}>
                  {c.tagName}
                </option>
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
              >
                All
              </button>
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
              {data.periods.length} {data.granularity === "month" ? "months" : "weeks"} ·{" "}
              {data.periods.reduce((s, p) => s + p.mention_count, 0).toLocaleString()} mentions
            </span>
          ) : null}
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

function drawHeatmap(
  ctx: CanvasRenderingContext2D,
  totalW: number,
  totalH: number,
  data: PriceMentionsResponse,
) {
  const chartW = totalW - AXIS_LEFT - AXIS_RIGHT;
  const chartH = totalH - AXIS_BOTTOM - AXIS_TOP;
  if (chartW <= 0 || chartH <= 0) return;

  const periods = data.periods;
  if (periods.length === 0) return;
  const binSize = data.bin_size;
  const numCols = periods.length;
  const colW = chartW / numCols;

  // Find global max count for color normalization
  let maxCount = 1;
  for (const p of periods) {
    for (const m of p.mentions) {
      if (m.count > maxCount) maxCount = m.count;
    }
  }

  ctx.clearRect(0, 0, totalW, totalH);

  // Chart background
  ctx.fillStyle = "rgba(0,0,0,0.18)";
  ctx.fillRect(AXIS_LEFT, AXIS_TOP, chartW, chartH);

  // Draw cells
  for (let ci = 0; ci < numCols; ci++) {
    const px = AXIS_LEFT + ci * colW;
    for (const m of periods[ci].mentions) {
      const y0 = priceToY(m.price_usd, chartH) + AXIS_TOP;
      const y1 = priceToY(m.price_usd + binSize, chartH) + AXIS_TOP;
      const cellH = Math.max(1, y1 - y0);
      ctx.fillStyle = countToColor(m.count, maxCount);
      ctx.fillRect(px, y0, colW + 0.5, cellH);
    }
  }

  // BTC price line
  ctx.save();
  ctx.strokeStyle = "rgba(255, 220, 60, 0.85)";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([3, 2]);
  ctx.beginPath();
  let firstBtc = true;
  for (let ci = 0; ci < numCols; ci++) {
    const btc = periods[ci].btc_close;
    if (btc == null || btc < 10_000 || btc > 10_000_000) continue;
    const x = AXIS_LEFT + (ci + 0.5) * colW;
    const y = priceToY(btc, chartH) + AXIS_TOP;
    if (firstBtc) {
      ctx.moveTo(x, y);
      firstBtc = false;
    } else {
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();
  ctx.restore();

  // Y axis labels (price)
  ctx.fillStyle = "rgba(180, 170, 160, 0.75)";
  ctx.font = "10px system-ui, sans-serif";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const yLabelPrices = [10_000, 20_000, 30_000, 50_000, 100_000, 200_000, 500_000, 1_000_000, 2_000_000, 5_000_000, 10_000_000];
  for (const price of yLabelPrices) {
    const y = priceToY(price, chartH) + AXIS_TOP;
    if (y < AXIS_TOP || y > AXIS_TOP + chartH) continue;
    ctx.fillText(priceFormatter.format(price), AXIS_LEFT - 4, y);
    // Tick mark
    ctx.fillStyle = "rgba(180, 170, 160, 0.25)";
    ctx.fillRect(AXIS_LEFT, y - 0.5, chartW, 1);
    ctx.fillStyle = "rgba(180, 170, 160, 0.75)";
  }

  // X axis labels (dates)
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  ctx.font = "10px system-ui, sans-serif";
  ctx.fillStyle = "rgba(180, 170, 160, 0.75)";
  const xLabelEvery = granularityLabelStep(numCols);
  for (let ci = 0; ci < numCols; ci += xLabelEvery) {
    const d = new Date(periods[ci].period_start);
    const label = data.granularity === "month" ? monthFormatter.format(d) : weekFormatter.format(d);
    const x = AXIS_LEFT + (ci + 0.5) * colW;
    ctx.fillText(label, x, AXIS_TOP + chartH + 4);
  }
}

function priceToY(price: number, chartH: number): number {
  const logP = Math.log10(Math.max(price, 1));
  const t = (logP - LOG_MIN) / (LOG_MAX - LOG_MIN);
  return chartH * (1 - t);
}

function countToColor(count: number, maxCount: number): string {
  if (count <= 0) return "transparent";
  const t = Math.pow(count / maxCount, 0.45); // sqrt-ish compression for visibility
  // Deep indigo → electric blue → teal → amber → red-orange
  let r: number, g: number, b: number, a: number;
  if (t < 0.25) {
    const s = t / 0.25;
    r = lerp(30, 40, s);
    g = lerp(60, 130, s);
    b = lerp(200, 240, s);
    a = lerp(0.35, 0.6, s);
  } else if (t < 0.55) {
    const s = (t - 0.25) / 0.3;
    r = lerp(40, 20, s);
    g = lerp(130, 180, s);
    b = lerp(240, 160, s);
    a = lerp(0.6, 0.75, s);
  } else if (t < 0.8) {
    const s = (t - 0.55) / 0.25;
    r = lerp(20, 245, s);
    g = lerp(180, 170, s);
    b = lerp(160, 20, s);
    a = lerp(0.75, 0.9, s);
  } else {
    const s = (t - 0.8) / 0.2;
    r = lerp(245, 255, s);
    g = lerp(170, 60, s);
    b = lerp(20, 20, s);
    a = lerp(0.9, 1.0, s);
  }
  return `rgba(${Math.round(r)},${Math.round(g)},${Math.round(b)},${a.toFixed(2)})`;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.max(0, Math.min(1, t));
}

function granularityLabelStep(numCols: number): number {
  if (numCols <= 12) return 1;
  if (numCols <= 36) return 3;
  if (numCols <= 72) return 6;
  if (numCols <= 156) return 13;
  return 26;
}
