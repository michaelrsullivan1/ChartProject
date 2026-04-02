export type BitcoinMention = {
  platform_tweet_id: string;
  url: string | null;
  text: string;
  created_at_platform: string;
  pricing_day: string;
  btc_price_usd: number;
  hypothetical_buy_amount_usd: number;
  hypothetical_btc_acquired: number;
  hypothetical_current_value_usd: number;
  price_change_since_tweet_pct: number;
  like_count: number | null;
  reply_count: number | null;
  repost_count: number | null;
};

export type BitcoinMentionsSummary = {
  total_tweet_count: number;
  candidate_tweet_count: number;
  mention_count: number;
  skipped_unpriced_mentions: number;
  buy_amount_usd: number;
  total_invested_usd: number;
  total_btc_accumulated: number;
  current_value_usd: number;
  total_return_usd: number;
  total_return_pct: number | null;
  average_entry_price_usd: number | null;
  median_entry_price_usd: number | null;
  first_mention_at: string | null;
  latest_mention_at: string | null;
  lowest_mention_price_usd: number | null;
  highest_mention_price_usd: number | null;
  best_timed_mention: BitcoinMention | null;
  worst_timed_mention: BitcoinMention | null;
  current_btc_price_usd: number;
  current_btc_price_as_of: string;
};

export type AuthorBitcoinMentionsResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
    profile_image_url: string | null;
  };
  phrase: {
    query: string;
    match_mode: string;
  };
  pricing: {
    asset_symbol: string;
    quote_currency: string;
    interval: string;
    methodology: string;
    current_price_usd: number;
    current_price_as_of: string;
  };
  btc_series: Array<{
    timestamp: string;
    price_usd: number;
  }>;
  summary: BitcoinMentionsSummary;
  cheapest_mentions: BitcoinMention[];
  latest_mentions: BitcoinMention[];
  mentions: BitcoinMention[];
};

export type BitcoinMentionsLeaderboardResponse = {
  view: string;
  phrase: {
    query: string;
    match_mode: string;
  };
  pricing: {
    asset_symbol: string;
    quote_currency: string;
    interval: string;
    methodology: string;
    current_price_usd: number;
    current_price_as_of: string;
  };
  buy_amount_usd: number;
  leaderboard: Array<{
    subject: {
      platform_user_id: string;
      username: string;
      display_name: string | null;
      profile_image_url: string | null;
    };
    total_tweet_count: number;
    candidate_tweet_count: number;
    mention_count: number;
    skipped_unpriced_mentions: number;
    buy_amount_usd: number;
    total_invested_usd: number;
    total_btc_accumulated: number;
    current_value_usd: number;
    total_return_usd: number;
    total_return_pct: number | null;
    average_entry_price_usd: number | null;
    median_entry_price_usd: number | null;
    first_mention_at: string | null;
    latest_mention_at: string | null;
    lowest_mention_price_usd: number | null;
    highest_mention_price_usd: number | null;
    best_timed_mention: BitcoinMention | null;
    worst_timed_mention: BitcoinMention | null;
    current_btc_price_usd: number;
    current_btc_price_as_of: string;
  }>;
};

export async function fetchAuthorBitcoinMentions(
  username: string,
  phrase = "bitcoin",
  buyAmountUsd = 10,
  signal?: AbortSignal,
): Promise<AuthorBitcoinMentionsResponse> {
  const params = new URLSearchParams({
    username,
    phrase,
    buy_amount_usd: String(buyAmountUsd),
  });
  const response = await fetch(`/api/views/bitcoin-mentions?${params.toString()}`, { signal });

  if (!response.ok) {
    throw new Error(`Bitcoin mentions request failed with status ${response.status}`);
  }

  return (await response.json()) as AuthorBitcoinMentionsResponse;
}

export async function fetchBitcoinMentionsLeaderboard(
  usernames: string[],
  phrase = "bitcoin",
  buyAmountUsd = 10,
  signal?: AbortSignal,
): Promise<BitcoinMentionsLeaderboardResponse> {
  const params = new URLSearchParams({
    phrase,
    buy_amount_usd: String(buyAmountUsd),
  });
  for (const username of usernames) {
    params.append("username", username);
  }

  const response = await fetch(`/api/views/bitcoin-mentions/leaderboard?${params.toString()}`, {
    signal,
  });

  if (!response.ok) {
    throw new Error(`Bitcoin mentions leaderboard request failed with status ${response.status}`);
  }

  return (await response.json()) as BitcoinMentionsLeaderboardResponse;
}
