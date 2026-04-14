export type AuthorRegistryDefinition = {
  slug: string;
  username: string;
  api_base_path: string;
};

export type BitcoinMentionsRegistryDefinition = {
  slug: string;
  username: string;
  api_base_path: string;
};

export type AuthorRegistryResponse = {
  view: string;
  generated_at: string;
  overviews: AuthorRegistryDefinition[];
  moods: AuthorRegistryDefinition[];
  heatmaps: AuthorRegistryDefinition[];
  bitcoin_mentions: BitcoinMentionsRegistryDefinition[];
  authors: Array<{
    user_id: number;
    platform_user_id: string;
    username: string;
    display_name: string | null;
    slug: string;
    published: boolean;
    sort_order: number | null;
    analysis_start: {
      overview: string | null;
      moods: string | null;
      heatmap: string | null;
    };
    readiness: {
      tweet_count: number;
      mood_scored_tweet_count: number;
      keyword_tweet_count: number;
      overview_ready: boolean;
      moods_ready: boolean;
      heatmap_ready: boolean;
      bitcoin_mentions_ready: boolean;
    };
    views: {
      overview: {
        enabled: boolean;
        ready: boolean;
        api_base_path: string;
      };
      moods: {
        enabled: boolean;
        ready: boolean;
        api_base_path: string;
      };
      heatmap: {
        enabled: boolean;
        ready: boolean;
        api_base_path: string;
      };
      bitcoin_mentions: {
        enabled: boolean;
        ready: boolean;
        api_base_path: string;
      };
    };
  }>;
};

export async function fetchAuthorRegistry(
  signal?: AbortSignal,
): Promise<AuthorRegistryResponse> {
  const response = await fetch("/api/author-registry", { signal });
  if (!response.ok) {
    throw new Error(`Author registry request failed with status ${response.status}`);
  }
  return (await response.json()) as AuthorRegistryResponse;
}
