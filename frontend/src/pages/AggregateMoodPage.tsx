import { useEffect, useState } from "react";
import { Pin } from "lucide-react";

import {
  fetchAggregateMarketSeries,
  fetchAggregateMoodCohorts,
  fetchAggregateOverview,
  fetchAuthorMoods,
  fetchBtcSpotPrice,
  type AggregateMarketSeriesResponse,
  type AggregateMoodCohortsResponse,
  type AggregateOverviewResponse,
  type AuthorMoodResponse,
  type BtcSpotPriceResponse,
} from "../api/authorOverview";
import {
  AuthorMoodTradingViewChart,
  type MoodVisualMode,
  type PriceMode,
} from "../components/AuthorMoodTradingViewChart";
import { DashboardLoadingState } from "../components/DashboardLoadingState";
import {
  type AggregateMoodDefinition,
  getAggregateMoodDescription,
} from "../config/aggregateMoods";
import { buildMoodDeviationSeries } from "../lib/moods";
import { type SentimentMode } from "../lib/sentiment";

const chartCurrencyFormatter = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

const integerFormatter = new Intl.NumberFormat("en-US");

const fullDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const compactDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const ALL_COHORT_KEY = "__all_tracked_users__";
const COMPARISON_LINE_COLOR = "rgba(198, 191, 180, 0.8)";

type CohortSelectionKey = string;

type AggregateMoodCohortOption = {
  key: CohortSelectionKey;
  tagSlug: string | null;
  tagName: string;
  userCount: number | null;
};

type AggregateMoodPageProps = {
  aggregateMood: AggregateMoodDefinition;
  showWatermark: boolean;
};

export function AggregateMoodPage({ aggregateMood, showWatermark }: AggregateMoodPageProps) {
  const [payload, setPayload] = useState<AggregateOverviewResponse | null>(null);
  const [moodPayload, setMoodPayload] = useState<AuthorMoodResponse | null>(null);
  const [comparisonMoodPayload, setComparisonMoodPayload] = useState<AuthorMoodResponse | null>(
    null,
  );
  const [marketPayload, setMarketPayload] = useState<AggregateMarketSeriesResponse | null>(null);
  const [btcSpotPayload, setBtcSpotPayload] = useState<BtcSpotPriceResponse | null>(null);
  const [cohortPayload, setCohortPayload] = useState<AggregateMoodCohortsResponse | null>(null);
  const [selectedCohortKey, setSelectedCohortKey] = useState<CohortSelectionKey>(ALL_COHORT_KEY);
  const [pinnedCohortKey, setPinnedCohortKey] = useState<CohortSelectionKey | null>(null);
  const [priceMode, setPriceMode] = useState<PriceMode>("btc");
  const [moodVisualMode, setMoodVisualMode] = useState<MoodVisualMode>("line");
  const [sentimentMode, setSentimentMode] = useState<SentimentMode>("weighted-8w");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const moodDescription = getAggregateMoodDescription(aggregateMood);

  useEffect(() => {
    setPinnedCohortKey(null);
  }, [aggregateMood.slug]);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const cohortResponse = await fetchAggregateMoodCohorts(aggregateMood.apiBasePath);
        const cohortOptions = buildAggregateMoodCohortOptions(cohortResponse.cohorts);
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
        const overviewPromise = fetchAggregateOverview(aggregateMood.apiBasePath, "week", undefined, {
          cohortTagSlug: effectiveSelectedCohortTagSlug,
        });
        const marketPromise = overviewPromise
          .then((response) =>
            fetchAggregateMarketSeries(
              aggregateMood.apiBasePath,
              response.range.start,
              response.range.end,
            ),
          )
          .then((response) => ({ ok: true as const, response }))
          .catch((marketError: unknown) => ({ ok: false as const, marketError }));
        const [requiredResponses, btcSpotResult, marketResult] = await Promise.all([
          Promise.all([
            overviewPromise,
            fetchAuthorMoods(aggregateMood.apiBasePath, "week", undefined, {
              cohortTagSlug: effectiveSelectedCohortTagSlug,
            }),
            effectiveComparisonCohortKey === null
              ? Promise.resolve(null)
              : fetchAuthorMoods(aggregateMood.apiBasePath, "week", undefined, {
                  cohortTagSlug: cohortKeyToTagSlug(effectiveComparisonCohortKey),
                }),
          ]),
          fetchBtcSpotPrice(aggregateMood.apiBasePath)
            .then((response) => ({ ok: true as const, response }))
            .catch((spotError: unknown) => ({ ok: false as const, spotError })),
          marketPromise,
        ]);
        const [response, moodResponse, comparisonMoodResponse] = requiredResponses;

        if (!cancelled) {
          setPayload(response);
          setMoodPayload(moodResponse);
          setComparisonMoodPayload(comparisonMoodResponse);
          setMarketPayload(marketResult.ok ? marketResult.response : null);
          setBtcSpotPayload(btcSpotResult.ok ? btcSpotResult.response : null);
          setCohortPayload(cohortResponse);
          if (selectedCohortKey !== effectiveSelectedCohortKey) {
            setSelectedCohortKey(effectiveSelectedCohortKey);
          }
          if (pinnedCohortKey !== effectivePinnedCohortKey) {
            setPinnedCohortKey(effectivePinnedCohortKey);
          }
          setError(null);
        }

        if (!btcSpotResult.ok) {
          console.warn(
            "ChartProject aggregate BTC spot request failed",
            aggregateMood.slug,
            btcSpotResult.spotError,
          );
        }
        if (!marketResult.ok) {
          console.warn(
            "ChartProject aggregate market series request failed",
            aggregateMood.slug,
            marketResult.marketError,
          );
        }
      } catch (loadError) {
        console.error("ChartProject aggregate mood request failed", aggregateMood.slug, loadError);
        if (!cancelled) {
          setError(loadError instanceof Error ? loadError.message : "Unknown mood fetch failure");
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
  }, [aggregateMood.apiBasePath, pinnedCohortKey, selectedCohortKey]);

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

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        {isLoading ? <DashboardLoadingState /> : null}
        {!payload || !moodPayload ? !isLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null : null}
        {payload && moodPayload ? (
          <AggregateMoodChartSection
            payload={payload}
            moodPayload={moodPayload}
            comparisonMoodPayload={comparisonMoodPayload}
            marketPayload={marketPayload}
            btcSpotPayload={btcSpotPayload}
            showWatermark={showWatermark}
            selectedMoodLabel={aggregateMood.moodLabel}
            moodDescription={moodDescription}
            priceMode={priceMode}
            onPriceModeChange={setPriceMode}
            moodVisualMode={moodVisualMode}
            onMoodVisualModeChange={setMoodVisualMode}
            sentimentMode={sentimentMode}
            onSentimentModeChange={setSentimentMode}
            cohortOptions={buildAggregateMoodCohortOptions(cohortPayload?.cohorts ?? [])}
            selectedCohortKey={selectedCohortKey}
            pinnedCohortKey={pinnedCohortKey}
            onSelectedCohortKeyChange={handleSelectedCohortKeyChange}
            onPinnedCohortKeyToggle={handlePinnedCohortKeyToggle}
          />
        ) : null}
      </article>
    </section>
  );
}

function AggregateMoodChartSection({
  payload,
  moodPayload,
  comparisonMoodPayload,
  marketPayload,
  btcSpotPayload,
  showWatermark,
  selectedMoodLabel,
  moodDescription,
  priceMode,
  onPriceModeChange,
  moodVisualMode,
  onMoodVisualModeChange,
  sentimentMode,
  onSentimentModeChange,
  cohortOptions,
  selectedCohortKey,
  pinnedCohortKey,
  onSelectedCohortKeyChange,
  onPinnedCohortKeyToggle,
}: {
  payload: AggregateOverviewResponse;
  moodPayload: AuthorMoodResponse;
  comparisonMoodPayload: AuthorMoodResponse | null;
  marketPayload: AggregateMarketSeriesResponse | null;
  btcSpotPayload: BtcSpotPriceResponse | null;
  showWatermark: boolean;
  selectedMoodLabel: string;
  moodDescription: string;
  priceMode: PriceMode;
  onPriceModeChange: (mode: PriceMode) => void;
  moodVisualMode: MoodVisualMode;
  onMoodVisualModeChange: (mode: MoodVisualMode) => void;
  sentimentMode: SentimentMode;
  onSentimentModeChange: (mode: SentimentMode) => void;
  cohortOptions: AggregateMoodCohortOption[];
  selectedCohortKey: CohortSelectionKey;
  pinnedCohortKey: CohortSelectionKey | null;
  onSelectedCohortKeyChange: (value: CohortSelectionKey) => void;
  onPinnedCohortKeyToggle: (value: CohortSelectionKey) => void;
}) {
  const chartPayload = {
    ...payload,
    btc_granularity: marketPayload?.btc_granularity ?? "day",
    mstr_granularity: marketPayload?.mstr_granularity ?? "day",
    btc_series: marketPayload?.btc_series ?? [],
    mstr_series: marketPayload?.mstr_series ?? [],
  };
  const latestBtcPoint = chartPayload.btc_series[chartPayload.btc_series.length - 1];
  const latestBtcDailyClose = latestBtcPoint?.price_usd ?? 0;
  const btcLastIso = latestBtcPoint?.timestamp ?? payload.range.end;
  const latestBtc = btcSpotPayload?.price_usd ?? latestBtcDailyClose;
  const moodDeviationSeries = buildMoodDeviationSeries(
    moodPayload,
    selectedMoodLabel,
    sentimentMode,
  );
  const currentMoodDeviation = getCurrentMoodDeviation(moodDeviationSeries, moodPayload.range.end);
  const moodExtremes = getMoodExtremes(moodDeviationSeries, moodPayload.range.end);
  const selectedMoodSummary = moodPayload.summary.moods[selectedMoodLabel];
  const cohortUserCount =
    moodPayload.summary.cohort_user_count ?? moodPayload.cohort?.user_count ?? 0;
  const cohortSelection = moodPayload.cohort?.selection ?? payload.cohort?.selection;
  const selectedCohortName =
    cohortSelection?.type === "tag"
      ? (cohortSelection.tag_name ?? formatMoodLabel(cohortSelection.tag_slug ?? ""))
      : "All tracked users";
  const pinnedCohortOption =
    pinnedCohortKey === null
      ? null
      : cohortOptions.find((cohortOption) => cohortOption.key === pinnedCohortKey) ?? null;
  const comparisonCohortName =
    comparisonMoodPayload && pinnedCohortOption ? pinnedCohortOption.tagName : null;

  return (
    <>
      <div className="metric-strip metric-strip-dashboard">
        <article className="metric-card">
          <p className="metric-label">Tracked users</p>
          <p className="metric-value">{integerFormatter.format(cohortUserCount)}</p>
          <p className="metric-note">{selectedCohortName}</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Analyzed posts</p>
          <p className="metric-value">
            {integerFormatter.format(moodPayload.summary.scored_tweet_count)}
          </p>
          <p className="metric-note">Scored posts across the tracked cohort</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Tracked mood</p>
          <p className="metric-value">{formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-note">Selected from the Aggregate Moods navigation</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Baseline mood score</p>
          <p className="metric-value">{formatPercent(selectedMoodSummary?.average_score ?? 0)}</p>
          <p className="metric-note">Average personal baseline across tracked users</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Latest BTC Price</p>
          <p className="metric-value">{chartCurrencyFormatter.format(latestBtc)}</p>
          <p className="metric-note">
            {btcSpotPayload
              ? `Coinbase spot on ${formatFullDate(btcSpotPayload.fetched_at)}`
              : `Price on ${formatFullDate(btcLastIso)}`}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Current Mood Deviation</p>
          <p className="metric-value">{formatSignedPercent(currentMoodDeviation.value)}</p>
          <p className="metric-note">
            {describeSentimentMode(sentimentMode, currentMoodDeviation.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Highest Aggregate {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.best.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(moodExtremes.best.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Lowest Aggregate {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.worst.value)}</p>
          <p className="metric-note">
            Week of {formatCompactDate(moodExtremes.worst.periodStart)}
          </p>
        </article>
      </div>

      <div className="chart-shell chart-shell-dashboard">
        <AuthorMoodTradingViewChart
          payload={chartPayload}
          moodPayload={moodPayload}
          comparisonMoodPayload={comparisonMoodPayload}
          comparisonMoodLabel={comparisonCohortName}
          comparisonMoodColor={COMPARISON_LINE_COLOR}
          showWatermark={showWatermark}
          showMoodSelector={false}
          moodDefinition={moodDescription}
          selectedMoodLabel={selectedMoodLabel}
          onMoodLabelChange={() => {}}
          priceMode={priceMode}
          onPriceModeChange={onPriceModeChange}
          moodVisualMode={moodVisualMode}
          onMoodVisualModeChange={onMoodVisualModeChange}
          sentimentMode={sentimentMode}
          smoothingWeightLabel="active user count"
          onSentimentModeChange={onSentimentModeChange}
          rightSidebarContent={
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
          }
        />
      </div>

      <div className="chart-caption-row chart-caption-row-dashboard">
        <div className="chart-legend" aria-label="Chart legend">
          {priceMode !== "mstr" ? (
            <span className="chart-legend-item">
              <span className="chart-swatch chart-swatch-btc" />
              BTC/USD line
            </span>
          ) : null}
          {priceMode !== "btc" ? (
            <span className="chart-legend-item">
              <span className="chart-swatch chart-swatch-mstr" />
              MSTR line
            </span>
          ) : null}
          <span className="chart-legend-item">
            <span className="chart-swatch chart-swatch-sentiment" />
            Aggregate {formatMoodLabel(selectedMoodLabel)} deviation
          </span>
          {comparisonMoodPayload && comparisonCohortName ? (
            <span className="chart-legend-item">
              <span className="chart-swatch chart-swatch-sentiment-comparison" />
              {comparisonCohortName} comparison line
            </span>
          ) : null}
        </div>
      </div>
    </>
  );
}

function buildAggregateMoodCohortOptions(
  cohorts: AggregateMoodCohortsResponse["cohorts"],
): AggregateMoodCohortOption[] {
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
  cohortOptions: AggregateMoodCohortOption[],
): boolean {
  return cohortOptions.some((cohortOption) => cohortOption.key === value);
}

function cohortKeyToTagSlug(value: CohortSelectionKey): string | null {
  return value === ALL_COHORT_KEY ? null : value;
}

function formatFullDate(value: string | number): string {
  return fullDateFormatter.format(normalizeDateValue(value));
}

function formatCompactDate(value: string): string {
  return compactDateFormatter.format(new Date(value));
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function formatSignedPercent(value: number): string {
  const percentage = value * 100;
  const formatted = percentage.toFixed(1);
  return percentage > 0 ? `+${formatted}%` : `${formatted}%`;
}

function describeSentimentMode(mode: SentimentMode, _periodStart: string): string {
  switch (mode) {
    case "weighted-4w":
      return "Smoothed using a 4-week WMA.";
    case "weighted-8w":
      return "Smoothed using an 8-week WMA.";
    case "weighted-12w":
      return "Smoothed using a 12-week WMA.";
    case "raw":
      return "Using the raw weekly score.";
  }
}

function getCurrentMoodDeviation(
  moodSeries: ReturnType<typeof buildMoodDeviationSeries>,
  fallbackPeriodStart: string,
): {
  periodStart: string;
  value: number;
} {
  const latestScoredPoint =
    [...moodSeries].reverse().find((point) => point.value !== null) ?? null;

  if (!latestScoredPoint) {
    return {
      periodStart: fallbackPeriodStart,
      value: 0,
    };
  }

  return {
    periodStart: latestScoredPoint.periodStart,
    value: latestScoredPoint.value ?? 0,
  };
}

function getMoodExtremes(
  moodSeries: ReturnType<typeof buildMoodDeviationSeries>,
  fallbackPeriodStart: string,
): {
  best: { periodStart: string; value: number };
  worst: { periodStart: string; value: number };
} {
  const scoredPoints = moodSeries.filter(
    (point): point is { periodStart: string; value: number } => point.value !== null,
  );

  if (scoredPoints.length === 0) {
    const fallback = {
      periodStart: fallbackPeriodStart,
      value: 0,
    };

    return {
      best: fallback,
      worst: fallback,
    };
  }

  let bestPoint = scoredPoints[0];
  let worstPoint = scoredPoints[0];

  for (const point of scoredPoints) {
    if (point.value > bestPoint.value) {
      bestPoint = point;
    }

    if (point.value < worstPoint.value) {
      worstPoint = point;
    }
  }

  return {
    best: {
      periodStart: bestPoint.periodStart,
      value: bestPoint.value,
    },
    worst: {
      periodStart: worstPoint.periodStart,
      value: worstPoint.value,
    },
  };
}

function formatMoodLabel(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

function normalizeDateValue(value: string | number): Date | number {
  return typeof value === "string" ? new Date(value) : value;
}
