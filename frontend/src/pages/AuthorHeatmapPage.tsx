import { useDeferredValue, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";

import {
  ColorType,
  LineSeries,
  LineType,
  createChart,
  type LineData,
  type MouseEventParams,
  type Time,
} from "lightweight-charts";

import {
  fetchAuthorKeywordHeatmap,
  fetchAuthorKeywordTopTweets,
  type AuthorKeywordHeatmapResponse,
  type AuthorKeywordTopTweetsResponse,
  type AuthorKeywordTrendResponse,
} from "../api/authorHeatmap";
import { DashboardLoadingState } from "../components/DashboardLoadingState";
import { TweetPreviewCard } from "../components/TweetPreviewCard";
import { type HeatmapDefinition } from "../config/heatmaps";
import { CHART_WATERMARK_HANDLE } from "../lib/watermark";

type HeatmapMode = "all" | "common" | "rising";
type WordCountFilter = "all" | "1" | "2" | "3";
type TrendPayloadMap = Record<string, AuthorKeywordTrendResponse>;

type AuthorHeatmapPageProps = {
  heatmap: HeatmapDefinition;
  showWatermark: boolean;
};

const integerFormatter = new Intl.NumberFormat("en-US");
const monthLabelFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});
const pinPalette = [
  "#ffb240",
  "#76c7ff",
  "#7af0b6",
  "#ff7d9c",
  "#d5a6ff",
  "#ffd86b",
  "#5fe0c8",
  "#ff9d5c",
];
const DEFAULT_HEATMAP_TOP_SECTION_RATIO = 0.39;
const HEATMAP_MIN_TOP_SECTION_HEIGHT = 220;
const HEATMAP_MIN_BOTTOM_SECTION_HEIGHT = 280;
const HEATMAP_RESIZE_HANDLE_HEIGHT = 14;
const HEATMAP_KEYBOARD_RESIZE_STEP = 24;

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

export function AuthorHeatmapPage({
  heatmap,
  showWatermark,
}: AuthorHeatmapPageProps) {
  const [mode, setMode] = useState<HeatmapMode>("common");
  const [wordCount, setWordCount] = useState<WordCountFilter>("all");
  const [phraseQuery, setPhraseQuery] = useState("");
  const [limit] = useState(48);
  const [payload, setPayload] = useState<AuthorKeywordHeatmapResponse | null>(null);
  const [pinnedPhrases, setPinnedPhrases] = useState<string[]>([]);
  const [activePhrase, setActivePhrase] = useState<string | null>(null);
  const [trendPayloads, setTrendPayloads] = useState<TrendPayloadMap>({});
  const [topTweetsPayload, setTopTweetsPayload] = useState<AuthorKeywordTopTweetsResponse | null>(
    null,
  );
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [isLoadingHeatmap, setIsLoadingHeatmap] = useState(true);
  const [isLoadingTweets, setIsLoadingTweets] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tweetError, setTweetError] = useState<string | null>(null);
  const [topSectionHeight, setTopSectionHeight] = useState<number | null>(null);
  const [isResizingLayout, setIsResizingLayout] = useState(false);
  const deferredPhraseQuery = useDeferredValue(phraseQuery);
  const layoutRef = useRef<HTMLDivElement | null>(null);
  const heatmapPanelRef = useRef<HTMLElement | null>(null);
  const resizeStateRef = useRef<{ startY: number; startHeight: number } | null>(null);
  const isPageSwitchLoading = isLoadingHeatmap && payload === null;

  useEffect(() => {
    setPayload(null);
    setPinnedPhrases([]);
    setActivePhrase(null);
    setTrendPayloads({});
    setTopTweetsPayload(null);
    setSelectedMonth(null);
    setError(null);
    setTweetError(null);
    setIsLoadingHeatmap(true);
  }, [heatmap.apiBasePath]);

  useEffect(() => {
    let cancelled = false;
    const controller = new AbortController();

    async function loadHeatmap() {
      setIsLoadingHeatmap(true);
      try {
        const response = await fetchAuthorKeywordHeatmap(
          heatmap.apiBasePath,
          { mode, wordCount, limit, phraseQuery: deferredPhraseQuery },
          controller.signal,
        );
        if (cancelled) {
          return;
        }

        setPayload(response);
        setError(null);
      } catch (loadError) {
        if (controller.signal.aborted || cancelled) {
          return;
        }

        setPayload(null);
        setError(
          loadError instanceof Error ? loadError.message : "Unknown narrative fetch failure",
        );
      } finally {
        if (!cancelled) {
          setIsLoadingHeatmap(false);
        }
      }
    }

    void loadHeatmap();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [deferredPhraseQuery, heatmap.apiBasePath, limit, mode, wordCount]);

  useEffect(() => {
    if (payload === null || pinnedPhrases.length === 0) {
      return;
    }

    const visibleRowsByPhrase = new Map(
      payload.rows.map((row) => [row.normalized_phrase, row] as const),
    );

    setTrendPayloads((current) => {
      let changed = false;
      const next = { ...current };

      for (const phrase of pinnedPhrases) {
        if (next[phrase] !== undefined) {
          continue;
        }
        const row = visibleRowsByPhrase.get(phrase);
        if (!row) {
          continue;
        }
        next[phrase] = buildTrendPayloadFromHeatmapRow(payload, row);
        changed = true;
      }

      return changed ? next : current;
    });
  }, [payload, pinnedPhrases]);

  useEffect(() => {
    if (pinnedPhrases.length === 0) {
      setActivePhrase(null);
      setSelectedMonth(null);
      setTopTweetsPayload(null);
      return;
    }

    setActivePhrase((current) => {
      if (current !== null && pinnedPhrases.includes(current)) {
        return current;
      }
      return pinnedPhrases[0] ?? null;
    });
  }, [pinnedPhrases]);

  useEffect(() => {
    if (activePhrase === null || selectedMonth === null) {
      setTopTweetsPayload(null);
      return;
    }

    const drilldownPhrase = activePhrase;
    const activeMonth = selectedMonth;
    let cancelled = false;
    const controller = new AbortController();

    async function loadTopTweets() {
      setIsLoadingTweets(true);
      setTweetError(null);
      try {
        const response = await fetchAuthorKeywordTopTweets(
          heatmap.apiBasePath,
          drilldownPhrase,
          activeMonth,
          controller.signal,
        );
        if (cancelled) {
          return;
        }

        setTopTweetsPayload(response);
      } catch (loadError) {
        if (controller.signal.aborted || cancelled) {
          return;
        }
        setTopTweetsPayload(null);
        setTweetError(
          loadError instanceof Error ? loadError.message : "Unknown top posts fetch failure",
        );
      } finally {
        if (!cancelled) {
          setIsLoadingTweets(false);
        }
      }
    }

    void loadTopTweets();

    return () => {
      cancelled = true;
      controller.abort();
    };
  }, [activePhrase, heatmap.apiBasePath, selectedMonth]);

  useEffect(() => {
    const layout = layoutRef.current;
    if (!layout) {
      return;
    }

    const resizeObserver = new ResizeObserver(() => {
      setTopSectionHeight((current) => {
        if (current === null) {
          return current;
        }
        return clampHeatmapTopSectionHeight(current, layout.clientHeight);
      });
    });
    resizeObserver.observe(layout);
    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!isResizingLayout) {
      return;
    }

    function handlePointerMove(event: PointerEvent) {
      const layout = layoutRef.current;
      const resizeState = resizeStateRef.current;
      if (!layout || !resizeState) {
        return;
      }

      setTopSectionHeight(
        clampHeatmapTopSectionHeight(
          resizeState.startHeight + (event.clientY - resizeState.startY),
          layout.clientHeight,
        ),
      );
    }

    function stopResizing() {
      resizeStateRef.current = null;
      setIsResizingLayout(false);
      document.body.style.removeProperty("cursor");
      document.body.style.removeProperty("user-select");
    }

    document.body.style.cursor = "row-resize";
    document.body.style.userSelect = "none";

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", stopResizing);
    window.addEventListener("pointercancel", stopResizing);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", stopResizing);
      window.removeEventListener("pointercancel", stopResizing);
      document.body.style.removeProperty("cursor");
      document.body.style.removeProperty("user-select");
    };
  }, [isResizingLayout]);

  const filteredRows = payload?.rows ?? [];

  const activeTrendPayload = activePhrase ? trendPayloads[activePhrase] ?? null : null;
  const heatmapLayoutStyle: CSSProperties = topSectionHeight
    ? {
        gridTemplateRows: `minmax(${HEATMAP_MIN_TOP_SECTION_HEIGHT}px, ${topSectionHeight}px) ${HEATMAP_RESIZE_HANDLE_HEIGHT}px minmax(${HEATMAP_MIN_BOTTOM_SECTION_HEIGHT}px, 1fr)`,
      }
    : {};

  function pinPhrase(phrase: string) {
    const matchingRow = payload?.rows.find((row) => row.normalized_phrase === phrase) ?? null;
    if (matchingRow && payload) {
      setTrendPayloads((current) =>
        current[phrase]
          ? current
          : {
              ...current,
              [phrase]: buildTrendPayloadFromHeatmapRow(payload, matchingRow),
            },
      );
    }
    setPinnedPhrases((current) => (current.includes(phrase) ? current : [...current, phrase]));
    setActivePhrase((current) => current ?? phrase);
  }

  function removePinnedPhrase(phrase: string) {
    setPinnedPhrases((current) => current.filter((value) => value !== phrase));
  }

  function beginHeatmapResize(event: React.PointerEvent<HTMLDivElement>) {
    if (event.pointerType === "mouse" && event.button !== 0) {
      return;
    }

    const layout = layoutRef.current;
    const panel = heatmapPanelRef.current;
    if (!layout || !panel) {
      return;
    }

    const currentHeight = panel.getBoundingClientRect().height;
    resizeStateRef.current = {
      startY: event.clientY,
      startHeight: currentHeight,
    };
    setTopSectionHeight(currentHeight);
    setIsResizingLayout(true);
    event.preventDefault();
  }

  function resizeHeatmapWithKeyboard(nextHeight: number) {
    const layout = layoutRef.current;
    const panel = heatmapPanelRef.current;
    if (!layout || !panel) {
      return;
    }

    const currentHeight = topSectionHeight ?? panel.getBoundingClientRect().height;
    setTopSectionHeight(
      clampHeatmapTopSectionHeight(currentHeight + nextHeight, layout.clientHeight),
    );
  }

  function handleHeatmapResizeKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowUp") {
      event.preventDefault();
      resizeHeatmapWithKeyboard(-HEATMAP_KEYBOARD_RESIZE_STEP);
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      resizeHeatmapWithKeyboard(HEATMAP_KEYBOARD_RESIZE_STEP);
      return;
    }

    if (event.key === "Home") {
      const layout = layoutRef.current;
      if (!layout) {
        return;
      }
      event.preventDefault();
      setTopSectionHeight(HEATMAP_MIN_TOP_SECTION_HEIGHT);
      return;
    }

    if (event.key === "End") {
      const layout = layoutRef.current;
      if (!layout) {
        return;
      }
      event.preventDefault();
      setTopSectionHeight(
        clampHeatmapTopSectionHeight(
          layout.clientHeight - HEATMAP_MIN_BOTTOM_SECTION_HEIGHT - HEATMAP_RESIZE_HANDLE_HEIGHT,
          layout.clientHeight,
        ),
      );
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      const layout = layoutRef.current;
      if (!layout) {
        return;
      }
      event.preventDefault();
      setTopSectionHeight(
        clampHeatmapTopSectionHeight(
          layout.clientHeight * DEFAULT_HEATMAP_TOP_SECTION_RATIO,
          layout.clientHeight,
        ),
      );
    }
  }

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace heatmap-workspace">
        {isPageSwitchLoading ? <DashboardLoadingState /> : null}
        {!isPageSwitchLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null}
        {!isPageSwitchLoading ? (
        <div
          ref={layoutRef}
          className={`heatmap-layout${isResizingLayout ? " is-resizing" : ""}`}
          style={heatmapLayoutStyle}
        >
          <section ref={heatmapPanelRef} className="heatmap-panel">
            <div className="heatmap-topbar">
              <div className="heatmap-toolbar">
                <div className="chart-control-card heatmap-control-card">
                  <p className="chart-control-eyebrow">Ranking</p>
                  <div className="chart-toggle-group heatmap-ranking-group">
                    <button
                      className={`chart-toggle-button${mode === "all" ? " is-active" : ""}`}
                      onClick={() => setMode("all")}
                      type="button"
                    >
                      All
                    </button>
                    <button
                      className={`chart-toggle-button${mode === "common" ? " is-active" : ""}`}
                      onClick={() => setMode("common")}
                      type="button"
                    >
                      Common
                    </button>
                    <button
                      className={`chart-toggle-button${mode === "rising" ? " is-active" : ""}`}
                      onClick={() => setMode("rising")}
                      type="button"
                    >
                      Rising
                    </button>
                  </div>
                </div>
                <div className="chart-control-card heatmap-control-card">
                  <p className="chart-control-eyebrow">Word Count</p>
                  <div className="chart-toggle-group chart-toggle-group-compact">
                    {([
                      ["all", "All"],
                      ["1", "1 word"],
                      ["2", "2 words"],
                      ["3", "3 words"],
                    ] as const).map(([value, label]) => (
                      <button
                        key={value}
                        className={`chart-toggle-button${wordCount === value ? " is-active" : ""}`}
                        onClick={() => setWordCount(value)}
                        type="button"
                      >
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="chart-control-card heatmap-control-card heatmap-search-card">
                  <div className="heatmap-search-header">
                    <p className="chart-control-eyebrow">Phrase Search</p>
                    <span className="heatmap-search-meta">
                      {integerFormatter.format(filteredRows.length)} matches
                    </span>
                  </div>
                  <label className="sr-only" htmlFor="heatmap-phrase-search">
                    Filter visible phrases
                  </label>
                  <input
                    id="heatmap-phrase-search"
                    className="heatmap-search-input"
                    onChange={(event) => setPhraseQuery(event.target.value)}
                    placeholder="Search all extracted phrases"
                    type="search"
                    value={phraseQuery}
                  />
                </div>
              </div>
            </div>

            <HeatmapGrid
              isLoading={isLoadingHeatmap}
              payload={payload}
              rows={filteredRows}
              pinnedPhrases={pinnedPhrases}
              activePhrase={activePhrase}
              onPinPhrase={pinPhrase}
            />
          </section>

          <div
            aria-label="Resize narrative sections"
            aria-orientation="horizontal"
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={
              layoutRef.current && heatmapPanelRef.current
                ? Math.round(
                    (100 * heatmapPanelRef.current.getBoundingClientRect().height) /
                      layoutRef.current.clientHeight,
                  )
                : Math.round(DEFAULT_HEATMAP_TOP_SECTION_RATIO * 100)
            }
            className="heatmap-resize-handle"
            onKeyDown={handleHeatmapResizeKeyDown}
            onPointerDown={beginHeatmapResize}
            role="separator"
            tabIndex={0}
            title="Drag to resize the narrative and pinned phrase sections"
          >
            <span className="heatmap-resize-grip" aria-hidden="true">
              <span />
              <span />
              <span />
            </span>
          </div>

          <section className="heatmap-bottom-layout">
            <div className="chart-shell chart-shell-dashboard heatmap-trend-shell">
              <KeywordTrendChart
                isLoading={false}
                activePhrase={activePhrase}
                activePayload={activeTrendPayload}
                error={null}
                pinnedPhrases={pinnedPhrases}
                trendPayloads={trendPayloads}
                selectedMonth={selectedMonth}
                showWatermark={showWatermark}
                onActivatePhrase={setActivePhrase}
                onRemovePhrase={removePinnedPhrase}
                onSelectMonth={(monthStart, phrase) => {
                  setActivePhrase(phrase);
                  setSelectedMonth(monthStart);
                }}
              />
            </div>

            <PhraseTweetPanel
              payload={topTweetsPayload}
              selectedMonth={selectedMonth}
              activePhrase={activePhrase}
              isLoading={isLoadingTweets}
              error={tweetError}
            />
          </section>
        </div>
        ) : null}
      </article>
    </section>
  );
}

function HeatmapGrid({
  isLoading,
  payload,
  rows,
  pinnedPhrases,
  activePhrase,
  onPinPhrase,
}: {
  isLoading: boolean;
  payload: AuthorKeywordHeatmapResponse | null;
  rows: AuthorKeywordHeatmapResponse["rows"];
  pinnedPhrases: string[];
  activePhrase: string | null;
  onPinPhrase: (phrase: string) => void;
}) {
  const maxCellCount = useMemo(() => {
    if (!payload || rows.length === 0) {
      return 0;
    }

    return rows.reduce(
      (rowMax, row) =>
        Math.max(
          rowMax,
          row.monthly_counts.reduce((cellMax, count) => Math.max(cellMax, count), 0),
        ),
      0,
    );
  }, [payload, rows]);

  if (isLoading && payload === null) {
    return <div className="heatmap-grid-empty">Loading phrase rows...</div>;
  }

  if (payload === null) {
    return <div className="heatmap-grid-empty">No phrase rows available for this filter.</div>;
  }

  if (rows.length === 0) {
    return <div className="heatmap-grid-empty">No phrases match this search.</div>;
  }

  const monthGridStyle: CSSProperties = {
    gridTemplateColumns: `repeat(${payload.months.length}, minmax(0, 1fr))`,
  };
  const monthLabelStep = Math.max(1, Math.ceil(payload.months.length / 10));

  return (
    <div className="heatmap-strip-shell">
      <div className="heatmap-strip-axis">
        <div className="heatmap-strip-label-header">Phrase</div>
        <div className="heatmap-strip-months" style={monthGridStyle}>
          {payload.months.map((month, index) => (
            <div
              key={month}
              className="heatmap-strip-month-label"
              title={formatMonthLabel(month)}
            >
              {index % monthLabelStep === 0 || index === payload.months.length - 1
                ? formatCompactMonthLabel(month)
                : ""}
            </div>
          ))}
        </div>
      </div>

      <div className="heatmap-strip-rows">
        {rows.map((row) => (
          <div
            key={row.normalized_phrase}
            className={`heatmap-strip-row${activePhrase === row.normalized_phrase ? " is-selected" : ""}${pinnedPhrases.includes(row.normalized_phrase) ? " is-pinned" : ""}`}
          >
            <div className="heatmap-strip-label-wrap">
              <button
                className="heatmap-strip-label"
                onClick={() => onPinPhrase(row.normalized_phrase)}
                type="button"
              >
                <span className="heatmap-strip-label-name">
                  {formatPhraseLabel(row.phrase)}
                </span>
                <span className="heatmap-strip-label-total">
                  {integerFormatter.format(row.total_matching_tweets)}
                </span>
              </button>
            </div>

            <div className="heatmap-strip-cells" style={monthGridStyle}>
              {row.monthly_counts.map((count, index) => (
                <button
                  key={`${row.normalized_phrase}-${payload.months[index]}`}
                  className={`heatmap-strip-cell${activePhrase === row.normalized_phrase ? " is-row-active" : ""}${pinnedPhrases.includes(row.normalized_phrase) ? " is-pinned" : ""}`}
                  onClick={() => onPinPhrase(row.normalized_phrase)}
                  style={{
                    backgroundColor: buildHeatmapCellColor(count, maxCellCount),
                  }}
                  title={`${formatPhraseLabel(row.phrase)} · ${formatMonthLabel(payload.months[index])} · ${integerFormatter.format(count)} tweets`}
                  type="button"
                >
                  <span className="sr-only">
                    {formatPhraseLabel(row.phrase)} {formatMonthLabel(payload.months[index])} {count}
                  </span>
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function KeywordTrendChart({
  isLoading,
  activePhrase,
  activePayload,
  error,
  pinnedPhrases,
  trendPayloads,
  selectedMonth,
  showWatermark,
  onActivatePhrase,
  onRemovePhrase,
  onSelectMonth,
}: {
  isLoading: boolean;
  activePhrase: string | null;
  activePayload: AuthorKeywordTrendResponse | null;
  error: string | null;
  pinnedPhrases: string[];
  trendPayloads: TrendPayloadMap;
  selectedMonth: string | null;
  showWatermark: boolean;
  onActivatePhrase: (phrase: string) => void;
  onRemovePhrase: (phrase: string) => void;
  onSelectMonth: (monthStart: string, phrase: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const visibleRangeRef = useRef<{ from: number; to: number } | null>(null);
  const [hoverPhrase, setHoverPhrase] = useState<string>("Hover a line");
  const [hoverLabel, setHoverLabel] = useState<string>("Month");
  const [hoverValue, setHoverValue] = useState<string>("Count");
  const visibleTrendPayloads = useMemo(
    () =>
      pinnedPhrases
        .map((phrase) => ({
          phrase,
          payload: trendPayloads[phrase] ?? null,
          color: getPinColor(pinnedPhrases.indexOf(phrase)),
        }))
        .filter(
          (
            entry,
          ): entry is {
            phrase: string;
            payload: AuthorKeywordTrendResponse;
            color: string;
          } => entry.payload !== null,
        ),
    [pinnedPhrases, trendPayloads],
  );

  useEffect(() => {
    if (!activePayload || !activePhrase) {
      return;
    }
    const latestPoint = activePayload.series[activePayload.series.length - 1];
    if (!latestPoint) {
      return;
    }

    setHoverPhrase(formatPhraseLabel(activePhrase));
    setHoverLabel(formatMonthLabel(latestPoint.period_start));
    setHoverValue(`${integerFormatter.format(latestPoint.matching_tweet_count)} tweets`);
  }, [activePayload, activePhrase]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || visibleTrendPayloads.length === 0) {
      return;
    }

    const chart = createChart(container, {
      ...chartOptions,
      width: container.clientWidth,
      height: container.clientHeight,
    });

    const seriesEntries = visibleTrendPayloads.map((entry) => {
      const series = chart.addSeries(LineSeries, {
        color: entry.color,
        lineWidth: activePhrase === entry.phrase ? 3 : 2,
        lineType: LineType.Curved,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: activePhrase === entry.phrase ? 4 : 3,
        crosshairMarkerBorderWidth: 2,
        crosshairMarkerBorderColor: entry.color,
        crosshairMarkerBackgroundColor: "#17130f",
      });

      const data: LineData<Time>[] = entry.payload.series.map((point) => ({
        time: toBusinessDay(point.period_start),
        value: point.matching_tweet_count,
      }));
      series.setData(data);
      return {
        phrase: entry.phrase,
        payload: entry.payload,
        series,
      };
    });
    const initialVisibleRange = visibleRangeRef.current;
    if (initialVisibleRange) {
      chart.timeScale().setVisibleLogicalRange(initialVisibleRange);
    } else {
      chart.timeScale().fitContent();
    }

    const handleCrosshairMove = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        const fallbackPhrase = activePhrase ?? seriesEntries[0]?.phrase ?? null;
        const fallbackPayload =
          (fallbackPhrase ? trendPayloads[fallbackPhrase] : null) ?? seriesEntries[0]?.payload ?? null;
        const latestPoint = fallbackPayload?.series[fallbackPayload.series.length - 1];
        if (fallbackPhrase && latestPoint) {
          setHoverPhrase(formatPhraseLabel(fallbackPhrase));
          setHoverLabel(formatMonthLabel(latestPoint.period_start));
          setHoverValue(`${integerFormatter.format(latestPoint.matching_tweet_count)} tweets`);
        }
        return;
      }

      const hoveredPhrase = resolveHoveredPhrase(param, seriesEntries, activePhrase);
      if (!hoveredPhrase) {
        return;
      }
      const matchingSeries = seriesEntries.find((entry) => entry.phrase === hoveredPhrase);
      const matchingPoint = matchingSeries
        ? findTrendPointForTime(param.time, matchingSeries.payload.series)
        : null;
      if (!matchingPoint) {
        return;
      }

      setHoverPhrase(formatPhraseLabel(hoveredPhrase));
      setHoverLabel(formatMonthLabel(matchingPoint.period_start));
      setHoverValue(`${integerFormatter.format(matchingPoint.matching_tweet_count)} tweets`);
    };

    const handleClick = (param: MouseEventParams<Time>) => {
      if (!param.point || !param.time) {
        return;
      }

      const hoveredPhrase = resolveHoveredPhrase(param, seriesEntries, activePhrase);
      if (!hoveredPhrase) {
        return;
      }
      const matchingSeries = seriesEntries.find((entry) => entry.phrase === hoveredPhrase);
      const matchingPoint = matchingSeries
        ? findTrendPointForTime(param.time, matchingSeries.payload.series)
        : null;
      if (!matchingPoint) {
        return;
      }

      onActivatePhrase(hoveredPhrase);
      onSelectMonth(matchingPoint.period_start, hoveredPhrase);
    };

    const handleVisibleLogicalRangeChange = (range: { from: number; to: number } | null) => {
      visibleRangeRef.current = range;
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);
    chart.subscribeClick(handleClick);
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange);

    const resizeObserver = new ResizeObserver(() => {
      chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight,
      });
    });
    resizeObserver.observe(container);

    return () => {
      visibleRangeRef.current = chart.timeScale().getVisibleLogicalRange();
      resizeObserver.disconnect();
      chart.unsubscribeCrosshairMove(handleCrosshairMove);
      chart.unsubscribeClick(handleClick);
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleVisibleLogicalRangeChange);
      chart.remove();
    };
  }, [activePhrase, onActivatePhrase, onSelectMonth, trendPayloads, visibleTrendPayloads]);

  return (
    <div className="heatmap-trend-layout">
        <div className="heatmap-trend-header">
          <div className="heatmap-trend-copy">
            <p className="chart-control-eyebrow">Pinned Phrases</p>
            <p className="heatmap-selection-title">
              {activePhrase ? formatPhraseLabel(activePhrase) : "Pin a phrase from the narrative"}
            </p>
            <div className="heatmap-pin-list">
            {pinnedPhrases.map((phrase, index) => (
              <div
                key={phrase}
                className={`heatmap-pin-chip${activePhrase === phrase ? " is-active" : ""}`}
                style={
                  {
                    "--pin-color": getPinColor(index),
                  } as CSSProperties
                }
              >
                <button
                  className="heatmap-pin-main"
                  onClick={() => onActivatePhrase(phrase)}
                  type="button"
                >
                  <span className="heatmap-pin-dot" aria-hidden="true" />
                  <span className="heatmap-pin-label">{formatPhraseLabel(phrase)}</span>
                </button>
                <button
                  aria-label={`Remove ${formatPhraseLabel(phrase)}`}
                  className="heatmap-pin-remove"
                  onClick={() => onRemovePhrase(phrase)}
                  type="button"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </div>
        <div className="heatmap-trend-stats">
          <div className="heatmap-mini-stat">
            <span className="heatmap-stat-label">Active</span>
            <span className="heatmap-stat-value">
              {activePhrase ? formatPhraseLabel(activePhrase) : "Pin a phrase"}
            </span>
          </div>
          <div className="heatmap-mini-stat">
            <span className="heatmap-stat-label">Hover phrase</span>
            <span className="heatmap-stat-value">{hoverPhrase}</span>
          </div>
          <div className="heatmap-mini-stat">
            <span className="heatmap-stat-label">Hover month</span>
            <span className="heatmap-stat-value">{hoverLabel}</span>
          </div>
          <div className="heatmap-mini-stat">
            <span className="heatmap-stat-label">Count</span>
            <span className="heatmap-stat-value">{hoverValue}</span>
          </div>
          <div className="heatmap-mini-stat">
            <span className="heatmap-stat-label">Selected month</span>
            <span className="heatmap-stat-value">
              {selectedMonth ? formatMonthLabel(selectedMonth) : "Click a month"}
            </span>
          </div>
        </div>
      </div>

      <div className="chart-stage">
        {showWatermark && visibleTrendPayloads.length > 0 ? (
          <div aria-hidden="true" className="chart-watermark">
            <span className="chart-watermark-handle">{CHART_WATERMARK_HANDLE}</span>
          </div>
        ) : null}
        {pinnedPhrases.length === 0 ? (
          <div className="heatmap-grid-empty">Click a phrase in the narrative to pin it here.</div>
        ) : null}
        {pinnedPhrases.length > 0 && isLoading && visibleTrendPayloads.length === 0 ? (
          <div className="heatmap-grid-empty">Loading pinned phrase trends...</div>
        ) : null}
        {pinnedPhrases.length > 0 && !isLoading && error ? (
          <div className="heatmap-grid-empty">{error}</div>
        ) : null}
        {visibleTrendPayloads.length > 0 ? (
          <div className="tradingview-chart heatmap-trend-chart" ref={containerRef} />
        ) : null}
      </div>
    </div>
  );
}

function PhraseTweetPanel({
  payload,
  selectedMonth,
  activePhrase,
  isLoading,
  error,
}: {
  payload: AuthorKeywordTopTweetsResponse | null;
  selectedMonth: string | null;
  activePhrase: string | null;
  isLoading: boolean;
  error: string | null;
}) {
  return (
    <section className="top-tweet-card phrase-tweet-panel">
      <p className="top-tweet-eyebrow">Phrase Drilldown</p>
      <p className="top-tweet-week">
        {activePhrase ? formatPhraseLabel(activePhrase) : "Pin a phrase"}
        {selectedMonth ? ` · ${formatMonthLabel(selectedMonth)}` : ""}
      </p>

      {!activePhrase ? (
        <p className="top-tweet-status">
          Pin a phrase in the narrative to inspect matching tweets.
        </p>
      ) : null}

      {activePhrase && !selectedMonth ? (
        <p className="top-tweet-status">
          Click a month on the trend chart to load the top liked tweets for the active pin.
        </p>
      ) : null}

      {isLoading ? <p className="top-tweet-status">Loading matching tweets...</p> : null}
      {error ? <p className="top-tweet-status">{error}</p> : null}
      {payload && payload.tweets.length === 0 ? (
        <p className="top-tweet-status">No matching tweets found for that month.</p>
      ) : null}

      {payload?.tweets.map((tweet) => {
        return (
          <TweetPreviewCard
            key={tweet.platform_tweet_id}
            author={payload.subject}
            className="phrase-tweet-card"
            tweet={tweet}
          />
        );
      })}
    </section>
  );
}

function buildHeatmapCellColor(count: number, maxCount: number): string {
  if (count === 0 || maxCount === 0) {
    return "rgba(255, 245, 220, 0.04)";
  }

  const intensity = Math.sqrt(count / maxCount);
  const alpha = 0.14 + intensity * 0.72;
  return `rgba(255, 178, 64, ${alpha.toFixed(3)})`;
}

function formatPhraseLabel(value: string): string {
  const uppercaseTokens = new Set([
    "btc",
    "mstr",
    "strc",
    "strd",
    "strf",
    "strk",
    "usd",
    "etf",
    "ai",
  ]);
  return value
    .split(" ")
    .map((token) => (uppercaseTokens.has(token) ? token.toUpperCase() : token))
    .join(" ");
}

function clampHeatmapTopSectionHeight(nextHeight: number, containerHeight: number): number {
  const maxTopHeight = Math.max(
    HEATMAP_MIN_TOP_SECTION_HEIGHT,
    containerHeight - HEATMAP_MIN_BOTTOM_SECTION_HEIGHT - HEATMAP_RESIZE_HANDLE_HEIGHT,
  );
  return Math.min(Math.max(nextHeight, HEATMAP_MIN_TOP_SECTION_HEIGHT), maxTopHeight);
}

function formatMonthLabel(value: string): string {
  return monthLabelFormatter.format(new Date(value));
}

function formatCompactMonthLabel(value: string): string {
  const formatted = formatMonthLabel(value);
  return formatted.replace(" 20", " ");
}

function toBusinessDay(value: string): Time {
  return value.slice(0, 10) as Time;
}

function findTrendPointForTime(
  time: Time,
  series: AuthorKeywordTrendResponse["series"],
): AuthorKeywordTrendResponse["series"][number] | null {
  const businessDay =
    typeof time === "string"
      ? time
      : typeof time === "object" && "year" in time
        ? `${time.year}-${`${time.month}`.padStart(2, "0")}-${`${time.day}`.padStart(2, "0")}`
        : null;
  if (businessDay === null) {
    return null;
  }
  return series.find((point) => point.period_start.startsWith(businessDay)) ?? null;
}

function resolveHoveredPhrase(
  param: MouseEventParams<Time>,
  seriesEntries: Array<{
    phrase: string;
    payload: AuthorKeywordTrendResponse;
    series: unknown;
  }>,
  activePhrase: string | null,
): string | null {
  const hoveredSeries = (
    param as MouseEventParams<Time> & {
      hoveredSeries?: unknown;
    }
  ).hoveredSeries;

  if (hoveredSeries !== undefined) {
    const matchingEntry = seriesEntries.find((entry) => entry.series === hoveredSeries);
    if (matchingEntry) {
      return matchingEntry.phrase;
    }
  }

  return activePhrase ?? seriesEntries[0]?.phrase ?? null;
}

function getPinColor(index: number): string {
  return pinPalette[index % pinPalette.length];
}

function buildTrendPayloadFromHeatmapRow(
  payload: AuthorKeywordHeatmapResponse,
  row: AuthorKeywordHeatmapResponse["rows"][number],
): AuthorKeywordTrendResponse {
  const series = payload.months.map((month, index) => ({
    period_start: month,
    matching_tweet_count: row.monthly_counts[index] ?? 0,
  }));

  return {
    view: `${payload.view}-derived-trend`,
    subject: payload.subject,
    phrase: row.phrase,
    normalized_phrase: row.normalized_phrase,
    word_count: row.word_count,
    granularity: "month",
    range: payload.range,
    summary: {
      total_matching_tweets: row.total_matching_tweets,
      peak_month_count: row.monthly_counts.reduce((max, count) => Math.max(max, count), 0),
    },
    series,
  };
}
