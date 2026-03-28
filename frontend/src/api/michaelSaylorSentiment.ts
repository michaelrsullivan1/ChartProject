export type MichaelSaylorSentimentResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  model: {
    model_key: string;
    granularity: string;
    status_filter: string;
  };
  range: {
    start: string;
    end: string;
  };
  summary: {
    scored_tweet_count: number;
    average_sentiment_index: number;
    average_confidence: number;
    negative_tweet_count: number;
    neutral_tweet_count: number;
    positive_tweet_count: number;
  };
  sentiment_series: Array<{
    period_start: string;
    scored_tweet_count: number;
    average_sentiment_index: number;
    average_confidence: number;
    average_negative_score: number;
    average_neutral_score: number;
    average_positive_score: number;
    negative_tweet_count: number;
    neutral_tweet_count: number;
    positive_tweet_count: number;
  }>;
};

export async function fetchMichaelSaylorSentiment(
  granularity: "day" | "week" = "week",
  signal?: AbortSignal,
): Promise<MichaelSaylorSentimentResponse> {
  const response = await fetch(
    `/api/views/michael-saylor-vs-btc/sentiment?granularity=${granularity}`,
    { signal },
  );

  if (!response.ok) {
    throw new Error(`Michael Saylor sentiment request failed with status ${response.status}`);
  }

  return (await response.json()) as MichaelSaylorSentimentResponse;
}
