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
  {
    slug: "walker-america",
    username: "WalkerAmerica",
    apiBasePath: "/api/views/walker-america-moods",
  },
  {
    slug: "chris-millas",
    username: "ChrisMMillas",
    apiBasePath: "/api/views/chris-millas-moods",
  },
  {
    slug: "richard-byworth",
    username: "RichardByworth",
    apiBasePath: "/api/views/richard-byworth-moods",
  },
  {
    slug: "andrew-webley",
    username: "asjwebley",
    apiBasePath: "/api/views/andrew-webley-moods",
  },
  {
    slug: "ray",
    username: "artificialsub",
    apiBasePath: "/api/views/ray-moods",
  },
  {
    slug: "stack-hodler",
    username: "stackhodler",
    apiBasePath: "/api/views/stack-hodler-moods",
  },
  {
    slug: "isabella",
    username: "isabellasg3",
    apiBasePath: "/api/views/isabella-moods",
  },
  {
    slug: "peter-schiff",
    username: "PeterSchiff",
    apiBasePath: "/api/views/peter-schiff-moods",
  },
  {
    slug: "michael-sullivan",
    username: "SullyMichaelvan",
    apiBasePath: "/api/views/michael-sullivan-moods",
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
