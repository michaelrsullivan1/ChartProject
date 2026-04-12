import type { AuthorMoodResponse } from "../api/authorOverview";
import type { SentimentMode } from "./sentiment";

export type MoodDeviationPoint = {
  periodStart: string;
  value: number | null;
};

export function buildMoodDeviationSeries(
  moodPayload: AuthorMoodResponse,
  moodLabel: string,
  sentimentMode: SentimentMode,
): MoodDeviationPoint[] {
  const baseline = moodPayload.summary.moods[moodLabel]?.average_score ?? 0;
  const weeklyPoints = moodPayload.mood_series;
  const usesPrecomputedDeviation =
    weeklyPoints.some((point) => point.moods[moodLabel]?.average_deviation !== undefined) ||
    moodPayload.summary.moods[moodLabel]?.average_deviation !== undefined;

  if (sentimentMode === "raw") {
    return weeklyPoints.map((point) => ({
      periodStart: point.period_start,
      value:
        getPointWeight(point) === 0
          ? null
          : getPointMoodDeviation(point, moodLabel, baseline, usesPrecomputedDeviation),
    }));
  }

  const windowSize =
    sentimentMode === "weighted-12w" ? 12 : sentimentMode === "weighted-8w" ? 8 : 4;

  return weeklyPoints.map((point, index) => ({
    periodStart: point.period_start,
    value:
      getPointWeight(point) === 0
        ? null
        : computeWeightedMoodDeviation(
            weeklyPoints,
            moodLabel,
            index,
            windowSize,
            baseline,
            usesPrecomputedDeviation,
          ),
  }));
}

function computeWeightedMoodDeviation(
  points: AuthorMoodResponse["mood_series"],
  moodLabel: string,
  endIndex: number,
  windowSize: number,
  baseline: number,
  usesPrecomputedDeviation: boolean,
): number {
  const startIndex = Math.max(0, endIndex - windowSize + 1);
  let weightedSum = 0;
  let totalWeight = 0;

  for (let index = startIndex; index <= endIndex; index += 1) {
    const point = points[index];
    if (!point) {
      continue;
    }

    const weight = getPointWeight(point);
    if (weight === 0) {
      continue;
    }

    weightedSum += getPointMoodDeviation(point, moodLabel, baseline, usesPrecomputedDeviation) * weight;
    totalWeight += weight;
  }

  if (totalWeight === 0) {
    return 0;
  }

  return usesPrecomputedDeviation ? weightedSum / totalWeight : weightedSum / totalWeight;
}

function getPointWeight(point: AuthorMoodResponse["mood_series"][number]): number {
  return point.active_user_count ?? point.scored_tweet_count;
}

function getPointMoodDeviation(
  point: AuthorMoodResponse["mood_series"][number],
  moodLabel: string,
  baseline: number,
  usesPrecomputedDeviation: boolean,
): number {
  if (usesPrecomputedDeviation) {
    return point.moods[moodLabel]?.average_deviation ?? 0;
  }

  return (point.moods[moodLabel]?.average_score ?? 0) - baseline;
}
