import { useEffect, useState } from "react";

import {
  fetchAggregateMoodCohorts,
  fetchAuthorMoods,
  fetchAuthorOverview,
  fetchBtcSpotPrice,
  type AggregateMoodCohortsResponse,
  type AuthorMoodResponse,
  type AuthorOverviewResponse,
  type BtcSpotPriceResponse,
} from "../api/authorOverview";
import {
  AuthorMoodTradingViewChart,
  type MoodVisualMode,
  type PriceMode,
} from "../components/AuthorMoodTradingViewChart";
import { ChartControlSelect } from "../components/ChartControlSelect";
import { DashboardLoadingState } from "../components/DashboardLoadingState";
import { getMoodDescriptionByLabel } from "../config/aggregateMoods";
import { type MoodDefinition } from "../lib/authorDefinitions";
import { buildMoodDeviationSeries } from "../lib/moods";
import { type SentimentMode } from "../lib/sentiment";

const integerFormatter = new Intl.NumberFormat("en-US");

const compactDateFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
});

const AGGREGATE_MOODS_API_BASE_PATH = "/api/views/aggregate-moods";
const NO_AGGREGATE_COMPARISON_KEY = "__no_aggregate_comparison__";
const ALL_AGGREGATE_COHORT_KEY = "__all_aggregate_users__";
const AGGREGATE_COMPARISON_COLOR = "rgba(198, 191, 180, 0.8)";
const MOOD_QUERY_PARAM = "mood";
const AGGREGATE_QUERY_PARAM = "aggregate";

type AggregateComparisonOption = {
  key: string;
  label: string;
};

type AuthorMoodPageProps = {
  mood: MoodDefinition;
  showWatermark: boolean;
};

export function AuthorMoodPage({ mood, showWatermark }: AuthorMoodPageProps) {
  const [payload, setPayload] = useState<AuthorOverviewResponse | null>(null);
  const [moodPayload, setMoodPayload] = useState<AuthorMoodResponse | null>(null);
  const [aggregateComparisonPayload, setAggregateComparisonPayload] = useState<AuthorMoodResponse | null>(
    null,
  );
  const [btcSpotPayload, setBtcSpotPayload] = useState<BtcSpotPriceResponse | null>(null);
  const [aggregateCohortPayload, setAggregateCohortPayload] =
    useState<AggregateMoodCohortsResponse | null>(null);
  const [selectedMoodLabel, setSelectedMoodLabel] = useState<string>("");
  const [selectedAggregateComparisonKey, setSelectedAggregateComparisonKey] =
    useState<string>(NO_AGGREGATE_COMPARISON_KEY);
  const [priceMode, setPriceMode] = useState<PriceMode>("btc");
  const [moodVisualMode, setMoodVisualMode] = useState<MoodVisualMode>("line");
  const [sentimentMode, setSentimentMode] = useState<SentimentMode>("weighted-8w");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const urlState = readAuthorMoodUrlState(window.location.hash, mood.slug);
    setSelectedMoodLabel(urlState.moodLabel ?? "");
    setSelectedAggregateComparisonKey(
      urlState.aggregateComparisonKey ?? NO_AGGREGATE_COMPARISON_KEY,
    );
  }, [mood.slug]);

  useEffect(() => {
    function handleHashChange() {
      const urlState = readAuthorMoodUrlState(window.location.hash, mood.slug);
      setSelectedMoodLabel(urlState.moodLabel ?? "");
      setSelectedAggregateComparisonKey(
        urlState.aggregateComparisonKey ?? NO_AGGREGATE_COMPARISON_KEY,
      );
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, [mood.slug]);

  useEffect(() => {
    if (!selectedMoodLabel) {
      return;
    }

    const nextHash = buildAuthorMoodHash(
      mood.slug,
      selectedMoodLabel,
      selectedAggregateComparisonKey,
    );

    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash;
    }
  }, [mood.slug, selectedMoodLabel, selectedAggregateComparisonKey]);

  useEffect(() => {
    let cancelled = false;

    async function loadView() {
      try {
        const [requiredResponses, btcSpotResult, aggregateCohortsResult, comparisonResult] =
          await Promise.all([
            Promise.all([
              fetchAuthorOverview(mood.apiBasePath, "week"),
              fetchAuthorMoods(mood.apiBasePath, "week"),
            ]),
            fetchBtcSpotPrice(mood.apiBasePath)
              .then((response) => ({ ok: true as const, response }))
              .catch((spotError: unknown) => ({ ok: false as const, spotError })),
            fetchAggregateMoodCohorts(AGGREGATE_MOODS_API_BASE_PATH)
              .then((response) => ({ ok: true as const, response }))
              .catch((cohortError: unknown) => ({ ok: false as const, cohortError })),
            selectedAggregateComparisonKey === NO_AGGREGATE_COMPARISON_KEY
              ? Promise.resolve({ ok: true as const, response: null })
              : fetchAuthorMoods(AGGREGATE_MOODS_API_BASE_PATH, "week", undefined, {
                  cohortTagSlug: aggregateComparisonKeyToTagSlug(selectedAggregateComparisonKey),
                })
                  .then((response) => ({ ok: true as const, response }))
                  .catch((comparisonError: unknown) => ({
                    ok: false as const,
                    comparisonError,
                  })),
          ]);
        const [response, moodResponse] = requiredResponses;
        const aggregateOptions = buildAggregateComparisonOptions(
          aggregateCohortsResult.ok ? aggregateCohortsResult.response.cohorts : [],
        );
        const effectiveAggregateComparisonKey = aggregateOptions.some(
          (option) => option.key === selectedAggregateComparisonKey,
        )
          ? selectedAggregateComparisonKey
          : NO_AGGREGATE_COMPARISON_KEY;

        if (!cancelled) {
          setPayload(response);
          setMoodPayload(moodResponse);
          setBtcSpotPayload(btcSpotResult.ok ? btcSpotResult.response : null);
          setAggregateCohortPayload(aggregateCohortsResult.ok ? aggregateCohortsResult.response : null);
          setAggregateComparisonPayload(
            comparisonResult.ok && effectiveAggregateComparisonKey !== NO_AGGREGATE_COMPARISON_KEY
              ? comparisonResult.response
              : null,
          );
          setSelectedMoodLabel((current) =>
            current && moodResponse.model.mood_labels.includes(current)
              ? current
              : (moodResponse.model.mood_labels[0] ?? "optimism"),
          );
          if (selectedAggregateComparisonKey !== effectiveAggregateComparisonKey) {
            setSelectedAggregateComparisonKey(effectiveAggregateComparisonKey);
          }
          setError(null);
        }

        if (!btcSpotResult.ok) {
          console.warn("ChartProject BTC spot request failed", mood.slug, btcSpotResult.spotError);
        }
        if (!aggregateCohortsResult.ok) {
          console.warn(
            "ChartProject aggregate cohorts request failed",
            mood.slug,
            aggregateCohortsResult.cohortError,
          );
        }
        if (!comparisonResult.ok) {
          console.warn(
            "ChartProject aggregate mood comparison request failed",
            mood.slug,
            comparisonResult.comparisonError,
          );
        }
      } catch (loadError) {
        console.error("ChartProject mood request failed", mood.slug, loadError);
        if (!cancelled) {
          setPayload(null);
          setMoodPayload(null);
          setAggregateComparisonPayload(null);
          setAggregateCohortPayload(null);
          setBtcSpotPayload(null);
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
    setPayload(null);
    setMoodPayload(null);
    setAggregateComparisonPayload(null);
    setAggregateCohortPayload(null);
    setBtcSpotPayload(null);
    void loadView();

    return () => {
      cancelled = true;
    };
  }, [mood, selectedAggregateComparisonKey]);

  return (
    <section className="dashboard-page">
      <article className="panel panel-accent dashboard-workspace">
        {isLoading ? <DashboardLoadingState /> : null}
        {!isLoading && error ? (
          <div className="dashboard-workspace-header">
            <p className="status-copy">{error}</p>
          </div>
        ) : null}
        {!isLoading && payload && moodPayload ? (
          <AuthorMoodChartSection
            payload={payload}
            moodPayload={moodPayload}
            aggregateComparisonPayload={aggregateComparisonPayload}
            aggregateComparisonOptions={buildAggregateComparisonOptions(
              aggregateCohortPayload?.cohorts ?? [],
            )}
            selectedAggregateComparisonKey={selectedAggregateComparisonKey}
            onAggregateComparisonKeyChange={setSelectedAggregateComparisonKey}
            showWatermark={showWatermark}
            selectedMoodLabel={selectedMoodLabel}
            onMoodLabelChange={setSelectedMoodLabel}
            priceMode={priceMode}
            onPriceModeChange={setPriceMode}
            moodVisualMode={moodVisualMode}
            onMoodVisualModeChange={setMoodVisualMode}
            sentimentMode={sentimentMode}
            onSentimentModeChange={setSentimentMode}
          />
        ) : null}
      </article>
    </section>
  );
}

function AuthorMoodChartSection({
  payload,
  moodPayload,
  aggregateComparisonPayload,
  aggregateComparisonOptions,
  selectedAggregateComparisonKey,
  onAggregateComparisonKeyChange,
  showWatermark,
  selectedMoodLabel,
  onMoodLabelChange,
  priceMode,
  onPriceModeChange,
  moodVisualMode,
  onMoodVisualModeChange,
  sentimentMode,
  onSentimentModeChange,
}: {
  payload: AuthorOverviewResponse;
  moodPayload: AuthorMoodResponse;
  aggregateComparisonPayload: AuthorMoodResponse | null;
  aggregateComparisonOptions: AggregateComparisonOption[];
  selectedAggregateComparisonKey: string;
  onAggregateComparisonKeyChange: (key: string) => void;
  showWatermark: boolean;
  selectedMoodLabel: string;
  onMoodLabelChange: (label: string) => void;
  priceMode: PriceMode;
  onPriceModeChange: (mode: PriceMode) => void;
  moodVisualMode: MoodVisualMode;
  onMoodVisualModeChange: (mode: MoodVisualMode) => void;
  sentimentMode: SentimentMode;
  onSentimentModeChange: (mode: SentimentMode) => void;
}) {
  const moodDeviationSeries = buildMoodDeviationSeries(
    moodPayload,
    selectedMoodLabel,
    sentimentMode,
  );
  const currentMoodDeviation = getCurrentMoodDeviation(moodDeviationSeries, moodPayload.range.end);
  const moodExtremes = getMoodExtremes(moodDeviationSeries, moodPayload.range.end);
  const moodDescription = getMoodDescriptionByLabel(selectedMoodLabel);
  const selectedAggregateComparison =
    aggregateComparisonOptions.find((option) => option.key === selectedAggregateComparisonKey) ?? null;
  const aggregateComparisonLabel =
    aggregateComparisonPayload &&
    selectedAggregateComparison &&
    selectedAggregateComparison.key !== NO_AGGREGATE_COMPARISON_KEY
      ? selectedAggregateComparison.label
      : null;

  return (
    <>
      <div className="metric-strip metric-strip-dashboard">
        <article className="metric-card">
          <p className="metric-label">Analyzed posts</p>
          <p className="metric-value">
            {integerFormatter.format(moodPayload.summary.scored_tweet_count)}
          </p>
          <p className="metric-note">Posts with stored mood scores</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Tracked mood</p>
          <p className="metric-value">{formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-note">Selected from the stored model labels</p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Current Mood Deviation</p>
          <p className="metric-value">{formatSignedPercent(currentMoodDeviation.value)}</p>
          <p className="metric-note">
            {describeSentimentMode(sentimentMode, currentMoodDeviation.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Highest {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.best.value)}</p>
          <p className="metric-note">
            Week ending {formatCompactDate(moodExtremes.best.periodStart)}
          </p>
        </article>
        <article className="metric-card">
          <p className="metric-label">Lowest {formatMoodLabel(selectedMoodLabel)}</p>
          <p className="metric-value">{formatSignedPercent(moodExtremes.worst.value)}</p>
          <p className="metric-note">
            Week ending {formatCompactDate(moodExtremes.worst.periodStart)}
          </p>
        </article>
      </div>

      <div className="chart-shell chart-shell-dashboard">
        <AuthorMoodTradingViewChart
          payload={payload}
          moodPayload={moodPayload}
          comparisonMoodPayload={aggregateComparisonPayload}
          comparisonMoodLabel={aggregateComparisonLabel}
          comparisonMoodColor={AGGREGATE_COMPARISON_COLOR}
          showWatermark={showWatermark}
          moodSelectorVariant="select"
          moodDefinition={moodDescription}
          selectedMoodLabel={selectedMoodLabel}
          onMoodLabelChange={onMoodLabelChange}
          priceMode={priceMode}
          onPriceModeChange={onPriceModeChange}
          moodVisualMode={moodVisualMode}
          onMoodVisualModeChange={onMoodVisualModeChange}
          sentimentMode={sentimentMode}
          onSentimentModeChange={onSentimentModeChange}
          rightSidebarSupplementalContent={
            <div className="chart-control-card">
              <p className="chart-control-eyebrow">Aggregate Comparison</p>
              <label className="chart-control-field">
                <span className="sr-only">Aggregate cohort comparison</span>
                <ChartControlSelect
                  ariaLabel="Aggregate cohort comparison"
                  onChange={onAggregateComparisonKeyChange}
                  options={aggregateComparisonOptions.map((option) => ({
                    value: option.key,
                    label: option.label,
                  }))}
                  value={selectedAggregateComparisonKey}
                />
              </label>
              <p className="chart-control-note">
                Uses the same selected mood and smoothing mode, overlaid as a muted aggregate line.
              </p>
              {aggregateComparisonLabel ? (
                <p className="chart-control-note">
                  Comparing against aggregate {aggregateComparisonLabel}.
                </p>
              ) : null}
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
            {formatMoodLabel(selectedMoodLabel)} deviation
          </span>
          {aggregateComparisonLabel ? (
            <span className="chart-legend-item">
              <span className="chart-swatch chart-swatch-sentiment-comparison" />
              Aggregate {aggregateComparisonLabel}
            </span>
          ) : null}
        </div>
      </div>
    </>
  );
}

function buildAggregateComparisonOptions(
  cohorts: AggregateMoodCohortsResponse["cohorts"],
): AggregateComparisonOption[] {
  return [
    {
      key: NO_AGGREGATE_COMPARISON_KEY,
      label: "No aggregate comparison",
    },
    {
      key: ALL_AGGREGATE_COHORT_KEY,
      label: "All tracked users",
    },
    ...cohorts.map((cohort) => ({
      key: cohort.tag_slug,
      label: cohort.tag_name,
    })),
  ];
}

function aggregateComparisonKeyToTagSlug(value: string): string | null {
  return value === ALL_AGGREGATE_COHORT_KEY || value === NO_AGGREGATE_COMPARISON_KEY ? null : value;
}

function buildAuthorMoodHash(
  moodSlug: string,
  selectedMoodLabel: string,
  selectedAggregateComparisonKey: string,
): string {
  const query = new URLSearchParams();
  query.set(MOOD_QUERY_PARAM, selectedMoodLabel);
  if (selectedAggregateComparisonKey !== NO_AGGREGATE_COMPARISON_KEY) {
    query.set(AGGREGATE_QUERY_PARAM, selectedAggregateComparisonKey);
  }

  const serializedQuery = query.toString();
  return `#/moods/${encodeURIComponent(moodSlug)}${serializedQuery ? `?${serializedQuery}` : ""}`;
}

function readAuthorMoodUrlState(
  hash: string,
  expectedMoodSlug: string,
): {
  moodLabel: string | null;
  aggregateComparisonKey: string | null;
} {
  const normalizedHash = hash.startsWith("#") ? hash.slice(1) : hash;
  const queryIndex = normalizedHash.indexOf("?");
  const path = queryIndex >= 0 ? normalizedHash.slice(0, queryIndex) : normalizedHash;
  if (!path.startsWith("/moods/")) {
    return {
      moodLabel: null,
      aggregateComparisonKey: null,
    };
  }

  const moodSlug = decodeURIComponent(path.slice("/moods/".length));
  if (moodSlug !== expectedMoodSlug) {
    return {
      moodLabel: null,
      aggregateComparisonKey: null,
    };
  }

  const queryString = queryIndex >= 0 ? normalizedHash.slice(queryIndex + 1) : "";
  const params = new URLSearchParams(queryString);
  const moodLabel = normalizeOptionalQueryParam(params.get(MOOD_QUERY_PARAM));
  const aggregateComparisonKey = normalizeOptionalQueryParam(params.get(AGGREGATE_QUERY_PARAM));

  return {
    moodLabel,
    aggregateComparisonKey,
  };
}

function normalizeOptionalQueryParam(value: string | null): string | null {
  if (value === null) {
    return null;
  }

  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

function formatCompactDate(value: string): string {
  return compactDateFormatter.format(new Date(value));
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
