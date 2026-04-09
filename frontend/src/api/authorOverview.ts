export type AuthorOverviewResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  cohort?: {
    user_count: number;
    usernames: string[];
    selection?: {
      type: "all" | "tag";
      tag_slug: string | null;
      tag_name: string | null;
    };
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

export type AggregateOverviewResponse = {
  view: string;
  generated_at?: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  cohort?: {
    user_count: number;
    usernames: string[];
    selection?: {
      type: "all" | "tag";
      tag_slug: string | null;
      tag_name: string | null;
    };
  };
  tweet_granularity: string;
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
  cohort?: {
    user_count: number;
    usernames: string[];
    selection?: {
      type: "all" | "tag";
      tag_slug: string | null;
      tag_name: string | null;
    };
  };
  model: {
    model_key: string;
    granularity: string;
    status_filter: string;
    mood_labels: string[];
    aggregation_mode?: string;
    baseline_mode?: string;
  };
  range: {
    start: string;
    end: string;
  };
  summary: {
    scored_tweet_count: number;
    cohort_user_count?: number;
    moods: Record<
      string,
      {
        average_score: number;
        average_deviation?: number;
        score_count: number;
      }
    >;
  };
  mood_series: Array<{
    period_start: string;
    scored_tweet_count: number;
    active_user_count?: number;
    moods: Record<
      string,
      {
        average_score: number;
        average_deviation?: number;
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

export type AggregateMoodCohortsResponse = {
  view: string;
  generated_at?: string;
  model: {
    model_key: string;
  };
  cohorts: Array<{
    tag_slug: string;
    tag_name: string;
    user_count: number;
    usernames: string[];
  }>;
  default_selection?: {
    type: "all";
    tag_slug: null;
    tag_name: string;
  };
};

export type AggregateMarketSeriesResponse = {
  view: string;
  btc_granularity: string;
  mstr_granularity: string;
  range: {
    start: string;
    end: string;
  };
  btc_series: Array<{
    timestamp: string;
    price_usd: number;
  }>;
  mstr_series: Array<{
    timestamp: string;
    price_usd: number;
  }>;
};

type AggregateMoodFilterOptions = {
  cohortTagSlug?: string | null;
};

export async function fetchAuthorOverview(
  endpointPath: string,
  granularity: "day" | "week" = "week",
  signal?: AbortSignal,
  options?: AggregateMoodFilterOptions,
): Promise<AuthorOverviewResponse> {
  const query = new URLSearchParams({ granularity });
  const cohortTagSlug = options?.cohortTagSlug?.trim();
  if (cohortTagSlug) {
    query.set("cohort_tag", cohortTagSlug);
  }

  const response = await fetch(`${endpointPath}?${query.toString()}`, { signal });

  if (!response.ok) {
    throw new Error(`Overview request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorOverviewResponse;
}

export async function fetchAggregateOverview(
  endpointPath: string,
  granularity: "day" | "week" = "week",
  signal?: AbortSignal,
  options?: AggregateMoodFilterOptions,
): Promise<AggregateOverviewResponse> {
  const query = new URLSearchParams({ granularity });
  const cohortTagSlug = options?.cohortTagSlug?.trim();
  if (cohortTagSlug) {
    query.set("cohort_tag", cohortTagSlug);
  }

  const response = await fetch(`${endpointPath}?${query.toString()}`, { signal });

  if (!response.ok) {
    throw new Error(`Aggregate overview request failed with status ${response.status}`);
  }

  return (await response.json()) as AggregateOverviewResponse;
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
  options?: AggregateMoodFilterOptions,
): Promise<AuthorMoodResponse> {
  const query = new URLSearchParams({ granularity });
  const cohortTagSlug = options?.cohortTagSlug?.trim();
  if (cohortTagSlug) {
    query.set("cohort_tag", cohortTagSlug);
  }

  const response = await fetch(`${endpointPath}/mood-series?${query.toString()}`, {
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

export async function fetchAggregateMoodCohorts(
  endpointPath: string,
  signal?: AbortSignal,
): Promise<AggregateMoodCohortsResponse> {
  const response = await fetch(`${endpointPath}/cohorts`, { signal });

  if (!response.ok) {
    throw new Error(`Aggregate cohort request failed with status ${response.status}`);
  }

  return (await response.json()) as AggregateMoodCohortsResponse;
}

export async function fetchAggregateMarketSeries(
  endpointPath: string,
  rangeStart: string,
  rangeEnd: string,
  signal?: AbortSignal,
): Promise<AggregateMarketSeriesResponse> {
  const query = new URLSearchParams({
    range_start: rangeStart,
    range_end: rangeEnd,
  });
  const response = await fetch(`${endpointPath}/market-series?${query.toString()}`, { signal });

  if (!response.ok) {
    throw new Error(`Aggregate market series request failed with status ${response.status}`);
  }

  return (await response.json()) as AggregateMarketSeriesResponse;
}
