import type { AggregateMoodCohortsResponse } from "../api/authorOverview";

export const ALL_PRICE_MENTION_COHORT_KEY = "__all__";
export const DEFAULT_PRICE_MENTION_WINDOW = "12m";
const COHORT_QUERY_PARAM = "cohort";
const PINNED_QUERY_PARAM = "pinned";
const WINDOW_QUERY_PARAM = "window";

export type PriceMentionCohortKey = string;

export type PriceMentionCohortOption = {
  key: PriceMentionCohortKey;
  tagSlug: string | null;
  tagName: string;
};

export type PriceMentionWindowKey = "3m" | "6m" | "12m" | "24m" | "all";

export const PRICE_MENTION_WINDOW_OPTIONS: Array<{
  key: PriceMentionWindowKey;
  label: string;
}> = [
  { key: "3m", label: "3M" },
  { key: "6m", label: "6M" },
  { key: "12m", label: "12M" },
  { key: "24m", label: "24M" },
  { key: "all", label: "All Common" },
];

export function buildPriceMentionCohortOptions(
  cohorts: AggregateMoodCohortsResponse["cohorts"],
): PriceMentionCohortOption[] {
  return [
    { key: ALL_PRICE_MENTION_COHORT_KEY, tagSlug: null, tagName: "All tracked users" },
    ...cohorts.map((cohort) => ({
      key: cohort.tag_slug,
      tagSlug: cohort.tag_slug,
      tagName: cohort.tag_name,
    })),
  ];
}

export function isValidPriceMentionCohortKey(
  value: string | null | undefined,
  cohortOptions: PriceMentionCohortOption[],
): value is PriceMentionCohortKey {
  return value != null && cohortOptions.some((cohortOption) => cohortOption.key === value);
}

export function getPriceMentionCohortTagSlug(
  cohortKey: PriceMentionCohortKey,
  cohortOptions: PriceMentionCohortOption[],
): string | null {
  return cohortOptions.find((cohortOption) => cohortOption.key === cohortKey)?.tagSlug ?? null;
}

export function getPinnedPriceMentionComparisonKey(
  selectedCohortKey: PriceMentionCohortKey,
  pinnedCohortKey: PriceMentionCohortKey | null,
): PriceMentionCohortKey | null {
  if (pinnedCohortKey === null || pinnedCohortKey === selectedCohortKey) {
    return null;
  }
  return pinnedCohortKey;
}

export function getNextPinnedPriceMentionCohortKey(
  selectedCohortKey: PriceMentionCohortKey,
  pinnedCohortKey: PriceMentionCohortKey | null,
  nextSelectedCohortKey: PriceMentionCohortKey,
): PriceMentionCohortKey | null {
  if (pinnedCohortKey === nextSelectedCohortKey && pinnedCohortKey !== selectedCohortKey) {
    return selectedCohortKey;
  }
  return pinnedCohortKey;
}

export function isValidPriceMentionWindowKey(
  value: string | null | undefined,
): value is PriceMentionWindowKey {
  return PRICE_MENTION_WINDOW_OPTIONS.some((option) => option.key === value);
}

export function buildPriceMentionSelectionHash(
  view: "distribution" | "zscore" | "spread",
  selectedCohortKey: PriceMentionCohortKey,
  pinnedCohortKey: PriceMentionCohortKey | null,
  timeWindow: PriceMentionWindowKey,
): string {
  const query = new URLSearchParams();
  query.set(COHORT_QUERY_PARAM, selectedCohortKey);
  if (pinnedCohortKey !== null) {
    query.set(PINNED_QUERY_PARAM, pinnedCohortKey);
  }
  query.set(WINDOW_QUERY_PARAM, timeWindow);
  return `#/price-mentions/${view}?${query.toString()}`;
}

export function readPriceMentionUrlState(
  hash: string,
  view: "distribution" | "zscore" | "spread",
): {
  selectedCohortKey: PriceMentionCohortKey | null;
  pinnedCohortKey: PriceMentionCohortKey | null;
  timeWindow: PriceMentionWindowKey;
} {
  const prefix = `#/price-mentions/${view}`;
  if (!hash.startsWith(prefix)) {
    return {
      selectedCohortKey: null,
      pinnedCohortKey: null,
      timeWindow: DEFAULT_PRICE_MENTION_WINDOW,
    };
  }

  const queryIndex = hash.indexOf("?");
  if (queryIndex < 0) {
    return {
      selectedCohortKey: null,
      pinnedCohortKey: null,
      timeWindow: DEFAULT_PRICE_MENTION_WINDOW,
    };
  }

  const params = new URLSearchParams(hash.slice(queryIndex + 1));
  const timeWindow = normalizeOptionalPriceMentionQueryParam(params.get(WINDOW_QUERY_PARAM));
  return {
    selectedCohortKey: normalizeOptionalPriceMentionQueryParam(
      params.get(COHORT_QUERY_PARAM),
    ),
    pinnedCohortKey: normalizeOptionalPriceMentionQueryParam(params.get(PINNED_QUERY_PARAM)),
    timeWindow: isValidPriceMentionWindowKey(timeWindow) ? timeWindow : DEFAULT_PRICE_MENTION_WINDOW,
  };
}

function normalizeOptionalPriceMentionQueryParam(value: string | null): string | null {
  const normalizedValue = value?.trim();
  return normalizedValue ? normalizedValue : null;
}
