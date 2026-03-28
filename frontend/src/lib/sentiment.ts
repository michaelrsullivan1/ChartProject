import type { MichaelSaylorSentimentResponse } from "../api/michaelSaylorSentiment";

export type SentimentMode = "raw" | "weighted-4w" | "weighted-8w" | "weighted-12w";

export type SentimentDeviationPoint = {
  periodStart: string;
  value: number | null;
};

export function buildSentimentDeviationSeries(
  sentimentPayload: MichaelSaylorSentimentResponse,
  sentimentMode: SentimentMode,
): SentimentDeviationPoint[] {
  const baseline = sentimentPayload.summary.average_sentiment_index;
  const weeklyPoints = sentimentPayload.sentiment_series;

  if (sentimentMode === "raw") {
    return weeklyPoints.map((point) => ({
      periodStart: point.period_start,
      value:
        point.scored_tweet_count === 0 ? null : point.average_sentiment_index - baseline,
    }));
  }

  const windowSize =
    sentimentMode === "weighted-12w" ? 12 : sentimentMode === "weighted-8w" ? 8 : 4;

  return weeklyPoints.map((point, index) => ({
    periodStart: point.period_start,
    value:
      point.scored_tweet_count === 0
        ? null
        : computeWeightedSentimentDeviation(weeklyPoints, index, windowSize, baseline),
  }));
}

function computeWeightedSentimentDeviation(
  points: MichaelSaylorSentimentResponse["sentiment_series"],
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

    weightedSum += point.average_sentiment_index * point.scored_tweet_count;
    totalWeight += point.scored_tweet_count;
  }

  if (totalWeight === 0) {
    return 0;
  }

  return weightedSum / totalWeight - baseline;
}
