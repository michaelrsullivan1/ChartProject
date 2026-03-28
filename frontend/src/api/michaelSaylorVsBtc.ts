export type MichaelSaylorVsBtcResponse = {
  view: string;
  subject: {
    platform_user_id: string;
    username: string;
    display_name: string | null;
  };
  tweet_granularity: string;
  btc_granularity: string;
  range: {
    start: string;
    end: string;
  };
  tweet_series: Array<{
    period_start: string;
    tweet_count: number;
    like_count: number;
  }>;
  btc_series: Array<{
    timestamp: string;
    price_usd: number;
  }>;
};

export async function fetchMichaelSaylorVsBtc(
  granularity: "day" | "week" = "week",
): Promise<MichaelSaylorVsBtcResponse> {
  const response = await fetch(`/api/views/michael-saylor-vs-btc?granularity=${granularity}`);

  if (!response.ok) {
    throw new Error(`Michael Saylor vs BTC request failed with status ${response.status}`);
  }

  return (await response.json()) as MichaelSaylorVsBtcResponse;
}
