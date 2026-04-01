export type AuthorKeywordHeatmapResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  mode: "all" | "common" | "rising";
  granularity: "month";
  range: {
    start: string;
    end: string;
  };
  filters: {
    word_count: "all" | "1" | "2" | "3";
    limit: number;
    phrase_query: string | null;
    analysis_start: string;
    extractor_key: string;
    extractor_version: string;
  };
  months: string[];
  rows: Array<{
    phrase: string;
    normalized_phrase: string;
    word_count: number;
    total_matching_tweets: number;
    ranking_score: number;
    monthly_counts: number[];
  }>;
};

export type AuthorKeywordTrendResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  phrase: string;
  normalized_phrase: string;
  word_count: number;
  granularity: "month";
  range: {
    start: string;
    end: string;
  };
  summary: {
    total_matching_tweets: number;
    peak_month_count: number;
  };
  series: Array<{
    period_start: string;
    matching_tweet_count: number;
  }>;
};

export type AuthorKeywordTopTweetsResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
    profile_image_url: string | null;
  };
  phrase: string;
  month: {
    start: string;
    end: string;
  };
  tweets: Array<{
    platform_tweet_id: string;
    url: string | null;
    text: string;
    created_at_platform: string;
    reply_count: number | null;
    repost_count: number | null;
    like_count: number | null;
    bookmark_count: number | null;
    impression_count: number | null;
  }>;
};

export async function fetchAuthorKeywordHeatmap(
  endpointPath: string,
  options: {
    mode: "all" | "common" | "rising";
    wordCount: "all" | "1" | "2" | "3";
    limit: number;
    phraseQuery?: string;
  },
  signal?: AbortSignal,
): Promise<AuthorKeywordHeatmapResponse> {
  const params = new URLSearchParams({
    mode: options.mode,
    word_count: options.wordCount,
    granularity: "month",
    limit: String(options.limit),
  });
  if (options.phraseQuery && options.phraseQuery.trim() !== "") {
    params.set("phrase_query", options.phraseQuery.trim());
  }

  const response = await fetch(
    `${endpointPath}?${params.toString()}`,
    { signal },
  );

  if (!response.ok) {
    throw new Error(`Heat map request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorKeywordHeatmapResponse;
}

export async function fetchAuthorKeywordTrend(
  endpointPath: string,
  phrase: string,
  signal?: AbortSignal,
): Promise<AuthorKeywordTrendResponse> {
  const response = await fetch(
    `${endpointPath}/phrase-trend?phrase=${encodeURIComponent(phrase)}&granularity=month`,
    { signal },
  );

  if (!response.ok) {
    throw new Error(`Phrase trend request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorKeywordTrendResponse;
}

export async function fetchAuthorKeywordTopTweets(
  endpointPath: string,
  phrase: string,
  monthStart: string,
  signal?: AbortSignal,
): Promise<AuthorKeywordTopTweetsResponse> {
  const response = await fetch(
    `${endpointPath}/top-liked-tweets?phrase=${encodeURIComponent(phrase)}&month_start=${encodeURIComponent(monthStart)}&limit=3`,
    { signal },
  );

  if (!response.ok) {
    throw new Error(`Phrase top posts request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorKeywordTopTweetsResponse;
}
