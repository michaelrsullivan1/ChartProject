export type AggregateNarrativeCohortsResponse = {
  view: string;
  generated_at?: string;
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

export type AggregateNarrativeResponse = {
  view: string;
  generated_at?: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  cohort: {
    user_count: number;
    usernames: string[];
    total_tweet_count?: number;
    selection: {
      type: "all" | "tag";
      tag_slug: string | null;
      tag_name: string | null;
    };
  };
  granularity: "week";
  range: {
    start: string;
    end: string;
  };
  cohort_series?: Array<{
    period_start: string;
    total_tweet_count: number;
  }>;
  default_narrative_slug: string | null;
  narratives: Array<{
    id: number;
    slug: string;
    name: string;
    phrase: string;
    summary: {
      total_matching_tweets: number;
      total_tweet_count?: number;
      total_mention_rate?: number;
      latest_period_count: number;
      latest_period_total_tweets?: number;
      latest_period_mention_rate?: number;
      peak_period_count: number;
      peak_period_total_tweets?: number;
      peak_period_mention_rate?: number;
    };
    series: Array<{
      period_start: string;
      matching_tweet_count: number;
      total_tweet_count?: number;
      mention_rate?: number;
    }>;
  }>;
};

type AggregateNarrativeFilterOptions = {
  cohortTagSlug?: string | null;
};

export async function fetchAggregateNarrativeCohorts(
  signal?: AbortSignal,
): Promise<AggregateNarrativeCohortsResponse> {
  const response = await fetch("/api/views/aggregate-narratives/cohorts", { signal });

  if (!response.ok) {
    throw new Error(`Aggregate narrative cohorts request failed with status ${response.status}`);
  }

  return (await response.json()) as AggregateNarrativeCohortsResponse;
}

export async function fetchAggregateNarratives(
  signal?: AbortSignal,
  options?: AggregateNarrativeFilterOptions,
): Promise<AggregateNarrativeResponse> {
  const query = new URLSearchParams({ granularity: "week" });
  const cohortTagSlug = options?.cohortTagSlug?.trim();
  if (cohortTagSlug) {
    query.set("cohort_tag", cohortTagSlug);
  }

  const response = await fetch(`/api/views/aggregate-narratives?${query.toString()}`, { signal });
  if (!response.ok) {
    throw new Error(`Aggregate narratives request failed with status ${response.status}`);
  }

  return (await response.json()) as AggregateNarrativeResponse;
}
