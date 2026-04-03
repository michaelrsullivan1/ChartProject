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

  if (sentimentMode === "raw") {
    return weeklyPoints.map((point) => ({
      periodStart: point.period_start,
      value:
        point.scored_tweet_count === 0
          ? null
          : (point.moods[moodLabel]?.average_score ?? 0) - baseline,
    }));
  }

  const windowSize =
    sentimentMode === "weighted-12w" ? 12 : sentimentMode === "weighted-8w" ? 8 : 4;

  return weeklyPoints.map((point, index) => ({
    periodStart: point.period_start,
    value:
      point.scored_tweet_count === 0
        ? null
        : computeWeightedMoodDeviation(weeklyPoints, moodLabel, index, windowSize, baseline),
  }));
}

function computeWeightedMoodDeviation(
  points: AuthorMoodResponse["mood_series"],
  moodLabel: string,
  endIndex: number,
  windowSize: number,
  baseline: number,
): number {
  const startIndex = Math.max(0, endIndex - windowSize + 1);
  let weightedSum = 0;
  let totalWeight = 0;

  for (let index = startIndex; index <= endIndex; index += 1) {
    const point = points[index];
    if (!point || point.scored_tweet_count === 0) {
      continue;
    }

    weightedSum += (point.moods[moodLabel]?.average_score ?? 0) * point.scored_tweet_count;
    totalWeight += point.scored_tweet_count;
  }

  if (totalWeight === 0) {
    return 0;
  }

  return weightedSum / totalWeight - baseline;
}
