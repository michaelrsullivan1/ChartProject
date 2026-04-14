export type OverviewDefinition = {
  slug: string;
  username: string;
  apiBasePath: string;
};

export type MoodDefinition = OverviewDefinition;
export type HeatmapDefinition = OverviewDefinition;

export type BitcoinMentionsDefinition = {
  slug: string;
  username: string;
  apiBasePath: string;
};

function getAuthorLabelFromSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getOverviewHash(slug: string): string {
  return `#/overviews/${slug}`;
}

export function getOverviewLabel(overview: OverviewDefinition): string {
  return getAuthorLabelFromSlug(overview.slug);
}

export function getOverviewTitle(overview: OverviewDefinition): string {
  return `${getOverviewLabel(overview)} Overview`;
}

export function getMoodHash(slug: string): string {
  return `#/moods/${slug}`;
}

export function getMoodLabel(mood: MoodDefinition): string {
  return getAuthorLabelFromSlug(mood.slug);
}

export function getMoodTitle(mood: MoodDefinition): string {
  return `${getMoodLabel(mood)} Moods`;
}

export function getHeatmapHash(slug: string): string {
  return `#/heatmaps/${slug}`;
}

export function getHeatmapLabel(heatmap: HeatmapDefinition): string {
  return getAuthorLabelFromSlug(heatmap.slug);
}

export function getHeatmapTitle(heatmap: HeatmapDefinition): string {
  return `${getHeatmapLabel(heatmap)} Narrative`;
}

export function getBitcoinMentionsHash(slug: string): string {
  return `#/bitcoin-mentions/${slug}`;
}

export function getBitcoinMentionsLabel(
  definition: BitcoinMentionsDefinition,
): string {
  return getAuthorLabelFromSlug(definition.slug);
}

export function getBitcoinMentionsTitle(
  definition: BitcoinMentionsDefinition,
): string {
  return `${getBitcoinMentionsLabel(definition)} Bitcoin Mentions`;
}
