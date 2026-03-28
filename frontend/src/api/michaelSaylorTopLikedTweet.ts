export type MichaelSaylorTopLikedTweetResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
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

export async function fetchMichaelSaylorTopLikedTweet(
  weekStart: string,
  signal?: AbortSignal,
): Promise<MichaelSaylorTopLikedTweetResponse> {
  const response = await fetch(
    `/api/views/michael-saylor-vs-btc/top-liked-tweet?week_start=${encodeURIComponent(weekStart)}`,
    { signal },
  );

  if (!response.ok) {
    throw new Error(`Michael Saylor top-liked-tweet request failed with status ${response.status}`);
  }

  return (await response.json()) as MichaelSaylorTopLikedTweetResponse;
}
