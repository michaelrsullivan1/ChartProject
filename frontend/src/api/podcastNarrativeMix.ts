export type PodcastNarrativeMixTopicRow = {
  topic: string;
  total_beliefs: number;
  overall_share: number;
  first_seen: string | null;
  last_seen: string | null;
  active_month_count: number;
  active_appearance_count: number;
};

export type PodcastNarrativeMixPeriodTopicRow = {
  topic: string;
  belief_count: number;
  topic_share: number;
};

export type PodcastNarrativeMixPeriodRow = {
  period_key: string;
  period_label: string;
  period_start: string | null;
  period_end: string | null;
  appearance_start_index: number | null;
  appearance_end_index: number | null;
  show_name: string | null;
  episode_title: string | null;
  appearance_count: number;
  total_beliefs: number;
  topic_labeled_beliefs: number;
  topics: PodcastNarrativeMixPeriodTopicRow[];
};

export type PodcastNarrativeMixTimelineMode = {
  mode: "month" | "appearance_index";
  label: string;
  periods: PodcastNarrativeMixPeriodRow[];
};

export type PodcastNarrativeMixResponse = {
  view: string;
  subject: {
    slug: string;
    name: string;
    source_person_id: string;
  };
  summary: {
    appearance_count: number;
    belief_count: number;
    range_start: string | null;
    range_end: string | null;
  };
  timeline_modes: {
    month: PodcastNarrativeMixTimelineMode;
    appearance_index: PodcastNarrativeMixTimelineMode;
  };
  topics: PodcastNarrativeMixTopicRow[];
  generated_at: string | null;
};

export async function fetchPodcastNarrativeMix(
  personSlug: string,
  options?: {
    signal?: AbortSignal;
  },
): Promise<PodcastNarrativeMixResponse> {
  const response = await fetch(
    `/api/views/podcasts/persons/${encodeURIComponent(personSlug)}/narrative-mix`,
    { signal: options?.signal },
  );

  if (!response.ok) {
    throw new Error(`Podcast narrative mix request failed with status ${response.status}`);
  }

  return (await response.json()) as PodcastNarrativeMixResponse;
}
