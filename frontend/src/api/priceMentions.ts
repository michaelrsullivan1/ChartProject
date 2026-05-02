export type PriceMentionItem = {
  price_usd: number;
  mention_type: string;
  count: number;
};

export type PriceMentionPeriod = {
  period_start: string;
  tweet_count: number;
  user_count: number;
  mention_count: number;
  mentions: PriceMentionItem[];
  btc_close: number | null;
};

export type PriceMentionsResponse = {
  granularity: string;
  cohort: {
    type: "all" | "tag";
    tag_slug: string | null;
    tag_name: string;
  };
  bin_size: number;
  extractor_key: string;
  extractor_version: string;
  periods: PriceMentionPeriod[];
  generated_at: string;
};

export async function fetchPriceMentions(
  apiBasePath: string,
  params: {
    granularity?: "month" | "week";
    cohortTag?: string | null;
    minConfidence?: number;
    mentionType?: string | null;
    binSize?: number;
  } = {},
  signal?: AbortSignal,
): Promise<PriceMentionsResponse> {
  const query = new URLSearchParams();
  if (params.granularity) query.set("granularity", params.granularity);
  if (params.cohortTag) query.set("cohort_tag", params.cohortTag);
  if (params.minConfidence != null) query.set("min_confidence", String(params.minConfidence));
  if (params.mentionType) query.set("mention_type", params.mentionType);
  if (params.binSize != null) query.set("bin_size", String(params.binSize));

  const response = await fetch(`${apiBasePath}?${query.toString()}`, { signal });
  if (!response.ok) throw new Error(`Price mentions request failed: ${response.status}`);
  return (await response.json()) as PriceMentionsResponse;
}
