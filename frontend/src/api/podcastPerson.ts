export type PodcastPersonResponse = {
  view: string;
  subject: {
    slug: string;
    name: string;
    source_person_id: string;
  };
  summary: {
    appearance_count: number;
    belief_count: number;
    source_total_beliefs: number | null;
    range_start: string | null;
    range_end: string | null;
  };
  top_shows: Array<{
    show_slug: string;
    show_name: string;
    appearance_count: number;
  }>;
  top_topics: Array<{
    topic: string;
    belief_count: number;
  }>;
  monthly_topic_counts: Array<{
    month_start: string;
    topic: string;
    belief_count: number;
  }>;
  appearances: Array<{
    published_at: string | null;
    show_name: string;
    episode_title: string;
  }>;
  recent_beliefs: Array<{
    published_at: string | null;
    show_name: string;
    episode_title: string;
    topic: string | null;
    atomic_belief: string;
    quote: string;
  }>;
};

export async function fetchPodcastPerson(
  personSlug: string,
  signal?: AbortSignal,
): Promise<PodcastPersonResponse> {
  const response = await fetch(`/api/views/podcasts/persons/${encodeURIComponent(personSlug)}`, {
    signal,
  });

  if (!response.ok) {
    throw new Error(`Podcast person request failed with status ${response.status}`);
  }

  return (await response.json()) as PodcastPersonResponse;
}
