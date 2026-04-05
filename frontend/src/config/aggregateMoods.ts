const aggregateMoodLabels = [
  "admiration",
  "amusement",
  "anger",
  "annoyance",
  "approval",
  "caring",
  "confusion",
  "curiosity",
  "desire",
  "disappointment",
  "disapproval",
  "disgust",
  "embarrassment",
  "excitement",
  "fear",
  "gratitude",
  "grief",
  "joy",
  "love",
  "nervousness",
  "neutral",
  "optimism",
  "pride",
  "realization",
  "relief",
  "remorse",
  "sadness",
  "surprise",
] as const;

export type AggregateMoodDefinition = {
  slug: string;
  moodLabel: string;
  apiBasePath: string;
};

export const aggregateMoodDefinitions: AggregateMoodDefinition[] = aggregateMoodLabels.map(
  (moodLabel) => ({
    slug: moodLabel.replace(/_/g, "-"),
    moodLabel,
    apiBasePath: "/api/views/aggregate-moods",
  }),
);

export function findAggregateMoodBySlug(slug: string): AggregateMoodDefinition | undefined {
  return aggregateMoodDefinitions.find((definition) => definition.slug === slug);
}

export function getAggregateMoodHash(slug: string): string {
  return `#/aggregate-moods/${slug}`;
}

export function getAggregateMoodLabel(definition: AggregateMoodDefinition): string {
  return definition.moodLabel
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getAggregateMoodTitle(definition: AggregateMoodDefinition): string {
  return `Aggregate ${getAggregateMoodLabel(definition)}`;
}
