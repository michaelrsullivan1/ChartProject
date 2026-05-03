import type { PriceMentionPeriod, PriceMentionsResponse } from "../api/priceMentions";
import type { PriceMentionWindowKey } from "./priceMentionCohorts";

const monthFormatter = new Intl.DateTimeFormat("en-US", {
  month: "short",
  year: "numeric",
  timeZone: "UTC",
});

export type WindowedPriceMentionComparison = {
  selectedPeriods: PriceMentionPeriod[];
  comparisonPeriods: PriceMentionPeriod[];
  windowStart: string | null;
  windowEnd: string | null;
  selectedFirstActive: string | null;
  comparisonFirstActive: string | null;
  selectedMentionCount: number;
  comparisonMentionCount: number;
  coverageSummary: string | null;
  coverageNote: string | null;
  timingNote: string | null;
};

export function resolveWindowedPriceMentionComparison(
  selectedData: PriceMentionsResponse | null,
  comparisonData: PriceMentionsResponse | null,
  timeWindow: PriceMentionWindowKey,
): WindowedPriceMentionComparison {
  const selectedPeriods = selectedData?.periods ?? [];
  const comparisonPeriods = comparisonData?.periods ?? [];
  const selectedFirstDate = parseFirstPeriodStart(selectedPeriods);
  const comparisonFirstDate = parseFirstPeriodStart(comparisonPeriods);
  const selectedLastDate = parseLastPeriodStart(selectedPeriods);
  const comparisonLastDate = parseLastPeriodStart(comparisonPeriods);

  const windowEnd = minDate(selectedLastDate, comparisonLastDate) ?? selectedLastDate;
  if (windowEnd === null) {
    return {
      selectedPeriods: [],
      comparisonPeriods: [],
      windowStart: null,
      windowEnd: null,
      selectedFirstActive: formatMonth(selectedFirstDate),
      comparisonFirstActive: formatMonth(comparisonFirstDate),
      selectedMentionCount: 0,
      comparisonMentionCount: 0,
      coverageSummary: null,
      coverageNote: null,
      timingNote: null,
    };
  }

  const windowStart =
    timeWindow === "all"
      ? maxDate(selectedFirstDate, comparisonFirstDate) ?? selectedFirstDate ?? windowEnd
      : addMonths(windowEnd, -(windowLengthMonths(timeWindow) - 1));

  const filteredSelectedPeriods = filterPeriodsByRange(selectedPeriods, windowStart, windowEnd);
  const filteredComparisonPeriods = filterPeriodsByRange(comparisonPeriods, windowStart, windowEnd);
  const selectedMentionCount = sumMentionCount(filteredSelectedPeriods);
  const comparisonMentionCount = sumMentionCount(filteredComparisonPeriods);
  const coverageSummary = `${formatWindowLabel(timeWindow)} window using common monthly coverage from ${formatMonth(windowStart)} through ${formatMonth(windowEnd)}.`;
  const coverageNote = comparisonData
    ? `${selectedData?.cohort.tag_name ?? "Selected cohort"} first active ${formatMonth(selectedFirstDate) ?? "n/a"}; ${comparisonData.cohort.tag_name} first active ${formatMonth(comparisonFirstDate) ?? "n/a"}.`
    : `${selectedData?.cohort.tag_name ?? "Selected cohort"} first active ${formatMonth(selectedFirstDate) ?? "n/a"}.`;
  const timingNote =
    timeWindow === "all" && comparisonData && selectedFirstDate && comparisonFirstDate
      ? `All Common starts at ${formatMonth(windowStart)} so older cohort history does not overweight earlier BTC price regimes.`
      : null;

  return {
    selectedPeriods: filteredSelectedPeriods,
    comparisonPeriods: filteredComparisonPeriods,
    windowStart: windowStart.toISOString(),
    windowEnd: windowEnd.toISOString(),
    selectedFirstActive: formatMonth(selectedFirstDate),
    comparisonFirstActive: formatMonth(comparisonFirstDate),
    selectedMentionCount,
    comparisonMentionCount,
    coverageSummary,
    coverageNote,
    timingNote,
  };
}

export function aggregatePriceMentionPeriodsIntoBuckets(
  periods: PriceMentionPeriod[],
  priceBuckets: number[],
): number[] {
  const counts = new Array<number>(priceBuckets.length).fill(0);
  for (const period of periods) {
    for (const mention of period.mentions) {
      const bucketIndex = findBucketIndex(mention.price_usd, priceBuckets);
      if (bucketIndex >= 0) {
        counts[bucketIndex] += mention.count;
      }
    }
  }
  return counts;
}

export function formatWindowLabel(timeWindow: PriceMentionWindowKey): string {
  switch (timeWindow) {
    case "3m":
      return "Last 3 months";
    case "6m":
      return "Last 6 months";
    case "12m":
      return "Last 12 months";
    case "24m":
      return "Last 24 months";
    case "all":
      return "All common history";
  }
}

function parseFirstPeriodStart(periods: PriceMentionPeriod[]): Date | null {
  return periods.length > 0 ? new Date(periods[0].period_start) : null;
}

function parseLastPeriodStart(periods: PriceMentionPeriod[]): Date | null {
  return periods.length > 0 ? new Date(periods[periods.length - 1].period_start) : null;
}

function filterPeriodsByRange(
  periods: PriceMentionPeriod[],
  start: Date,
  end: Date,
): PriceMentionPeriod[] {
  const startTime = start.getTime();
  const endTime = end.getTime();
  return periods.filter((period) => {
    const periodTime = new Date(period.period_start).getTime();
    return periodTime >= startTime && periodTime <= endTime;
  });
}

function sumMentionCount(periods: PriceMentionPeriod[]): number {
  return periods.reduce((total, period) => total + period.mention_count, 0);
}

function findBucketIndex(price: number, priceBuckets: number[]): number {
  for (let index = priceBuckets.length - 1; index >= 0; index -= 1) {
    if (price >= priceBuckets[index]) {
      return index;
    }
  }
  return -1;
}

function windowLengthMonths(timeWindow: Exclude<PriceMentionWindowKey, "all">): number {
  switch (timeWindow) {
    case "3m":
      return 3;
    case "6m":
      return 6;
    case "12m":
      return 12;
    case "24m":
      return 24;
  }
}

function addMonths(value: Date, monthOffset: number): Date {
  return new Date(Date.UTC(value.getUTCFullYear(), value.getUTCMonth() + monthOffset, 1));
}

function minDate(left: Date | null, right: Date | null): Date | null {
  if (left === null) return right;
  if (right === null) return left;
  return left.getTime() <= right.getTime() ? left : right;
}

function maxDate(left: Date | null, right: Date | null): Date | null {
  if (left === null) return right;
  if (right === null) return left;
  return left.getTime() >= right.getTime() ? left : right;
}

function formatMonth(value: Date | null): string | null {
  return value ? monthFormatter.format(value) : null;
}
