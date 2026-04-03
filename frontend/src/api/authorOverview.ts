export type AuthorOverviewResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  tweet_granularity: string;
  btc_granularity: string;
  mstr_granularity: string;
  range: {
    start: string;
    end: string;
  };
  tweet_series: Array<{
    period_start: string;
    tweet_count: number;
    like_count: number;
    bookmark_count: number;
    impression_count: number;
  }>;
  btc_series: Array<{
    timestamp: string;
    price_usd: number;
  }>;
  mstr_series: Array<{
    timestamp: string;
    price_usd: number;
  }>;
};

export type AuthorSentimentResponse = {
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

export type AuthorTopLikedTweetResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
    profile_image_url: string | null;
  };
  week: {
    start: string;
    end: string;
  };
  top_tweet: null | {
    platform_tweet_id: string;
    url: string | null;
    text: string;
    created_at_platform: string;
    reply_count: number | null;
    repost_count: number | null;
    like_count: number | null;
    bookmark_count: number | null;
  };
};

export type AuthorMoodResponse = {
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
    mood_labels: string[];
  };
  range: {
    start: string;
    end: string;
  };
  summary: {
    scored_tweet_count: number;
    moods: Record<
      string,
      {
        average_score: number;
        score_count: number;
      }
    >;
  };
  mood_series: Array<{
    period_start: string;
    scored_tweet_count: number;
    moods: Record<
      string,
      {
        average_score: number;
        score_count: number;
      }
    >;
  }>;
};

export type BtcSpotPriceResponse = {
  asset_symbol: string;
  quote_currency: string;
  price_usd: number;
  fetched_at: string;
  source_name: string;
};

export async function fetchAuthorOverview(
  endpointPath: string,
  granularity: "day" | "week" = "week",
  signal?: AbortSignal,
): Promise<AuthorOverviewResponse> {
  const response = await fetch(`${endpointPath}?granularity=${granularity}`, { signal });

  if (!response.ok) {
    throw new Error(`Overview request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorOverviewResponse;
}

export async function fetchAuthorSentiment(
  endpointPath: string,
  granularity: "day" | "week" = "week",
  signal?: AbortSignal,
): Promise<AuthorSentimentResponse> {
  const response = await fetch(`${endpointPath}/sentiment?granularity=${granularity}`, {
    signal,
  });

  if (!response.ok) {
    throw new Error(`Sentiment request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorSentimentResponse;
}

export async function fetchAuthorMoods(
  endpointPath: string,
  granularity: "day" | "week" = "week",
  signal?: AbortSignal,
): Promise<AuthorMoodResponse> {
  const response = await fetch(`${endpointPath}/mood-series?granularity=${granularity}`, {
    signal,
  });

  if (!response.ok) {
    throw new Error(`Mood request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorMoodResponse;
}

export async function fetchAuthorTopLikedTweet(
  endpointPath: string,
  weekStart: string,
  signal?: AbortSignal,
): Promise<AuthorTopLikedTweetResponse> {
  const response = await fetch(
    `${endpointPath}/top-liked-tweet?week_start=${encodeURIComponent(weekStart)}`,
    { signal },
  );

  if (!response.ok) {
    throw new Error(`Top liked post request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorTopLikedTweetResponse;
}

export async function fetchBtcSpotPrice(
  endpointPath: string,
  signal?: AbortSignal,
): Promise<BtcSpotPriceResponse> {
  const response = await fetch(`${endpointPath}/btc-spot`, { signal });

  if (!response.ok) {
    throw new Error(`BTC spot request failed with status ${response.status}`);
  }

  return (await response.json()) as BtcSpotPriceResponse;
}
