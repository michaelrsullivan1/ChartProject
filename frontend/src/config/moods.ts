export type MoodDefinition = {
  slug: string;
  username: string;
  apiBasePath: string;
};

export const moodDefinitions: MoodDefinition[] = [
  {
    slug: "michael-saylor",
    username: "saylor",
    apiBasePath: "/api/views/michael-saylor-moods",
  },
];

export function findMoodBySlug(slug: string): MoodDefinition | undefined {
  return moodDefinitions.find((mood) => mood.slug === slug);
}

export function getMoodHash(slug: string): string {
  return `#/moods/${slug}`;
}

export function getMoodLabel(mood: MoodDefinition): string {
  return mood.slug
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getMoodTitle(mood: MoodDefinition): string {
  return `${getMoodLabel(mood)} Moods`;
}
