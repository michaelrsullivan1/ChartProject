import type { AggregateMoodCohortsResponse } from "../api/authorOverview";

export const ALL_PRICE_MENTION_COHORT_KEY = "__all__";
const COHORT_QUERY_PARAM = "cohort";
const PINNED_QUERY_PARAM = "pinned";

export type PriceMentionCohortKey = string;

export type PriceMentionCohortOption = {
  key: PriceMentionCohortKey;
  tagSlug: string | null;
  tagName: string;
};

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

export function buildPriceMentionSelectionHash(
  view: "distribution" | "zscore",
  selectedCohortKey: PriceMentionCohortKey,
  pinnedCohortKey: PriceMentionCohortKey | null,
): string {
  const query = new URLSearchParams();
  query.set(COHORT_QUERY_PARAM, selectedCohortKey);
  if (pinnedCohortKey !== null) {
    query.set(PINNED_QUERY_PARAM, pinnedCohortKey);
  }
  return `#/price-mentions/${view}?${query.toString()}`;
}

export function readPriceMentionUrlState(
  hash: string,
  view: "distribution" | "zscore",
): {
  selectedCohortKey: PriceMentionCohortKey | null;
  pinnedCohortKey: PriceMentionCohortKey | null;
} {
  const prefix = `#/price-mentions/${view}`;
  if (!hash.startsWith(prefix)) {
    return {
      selectedCohortKey: null,
      pinnedCohortKey: null,
    };
  }

  const queryIndex = hash.indexOf("?");
  if (queryIndex < 0) {
    return {
      selectedCohortKey: ALL_PRICE_MENTION_COHORT_KEY,
      pinnedCohortKey: null,
    };
  }

  const params = new URLSearchParams(hash.slice(queryIndex + 1));
  return {
    selectedCohortKey: normalizeOptionalPriceMentionQueryParam(
      params.get(COHORT_QUERY_PARAM),
    ) ?? ALL_PRICE_MENTION_COHORT_KEY,
    pinnedCohortKey: normalizeOptionalPriceMentionQueryParam(params.get(PINNED_QUERY_PARAM)),
  };
}

function normalizeOptionalPriceMentionQueryParam(value: string | null): string | null {
  const normalizedValue = value?.trim();
  return normalizedValue ? normalizedValue : null;
}
