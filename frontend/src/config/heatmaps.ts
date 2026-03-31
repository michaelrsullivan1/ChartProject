export type HeatmapDefinition = {
  slug: string;
  username: string;
  apiBasePath: string;
};

export const heatmapDefinitions: HeatmapDefinition[] = [
  {
    slug: "michael-saylor",
    username: "saylor",
    apiBasePath: "/api/views/michael-saylor-heatmap",
  },
];

export function findHeatmapBySlug(slug: string): HeatmapDefinition | undefined {
  return heatmapDefinitions.find((heatmap) => heatmap.slug === slug);
}

export function getHeatmapHash(slug: string): string {
  return `#/heatmaps/${slug}`;
}

export function getHeatmapLabel(heatmap: HeatmapDefinition): string {
  return heatmap.slug
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getHeatmapTitle(heatmap: HeatmapDefinition): string {
  return `${getHeatmapLabel(heatmap)} Heat Map`;
}
