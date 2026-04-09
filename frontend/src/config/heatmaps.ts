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
  {
    slug: "walker-america",
    username: "WalkerAmerica",
    apiBasePath: "/api/views/walker-america-heatmap",
  },
  {
    slug: "chris-millas",
    username: "ChrisMMillas",
    apiBasePath: "/api/views/chris-millas-heatmap",
  },
  {
    slug: "richard-byworth",
    username: "RichardByworth",
    apiBasePath: "/api/views/richard-byworth-heatmap",
  },
  {
    slug: "andrew-webley",
    username: "asjwebley",
    apiBasePath: "/api/views/andrew-webley-heatmap",
  },
  {
    slug: "michael-sullivan",
    username: "SullyMichaelvan",
    apiBasePath: "/api/views/michael-sullivan-heatmap",
  },
  {
    slug: "peter-schiff",
    username: "PeterSchiff",
    apiBasePath: "/api/views/peter-schiff-heatmap",
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
