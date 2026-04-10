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
    slug: "ray",
    username: "artificialsub",
    apiBasePath: "/api/views/ray-heatmap",
  },
  {
    slug: "stack-hodler",
    username: "stackhodler",
    apiBasePath: "/api/views/stack-hodler-heatmap",
  },
  {
    slug: "isabella",
    username: "isabellasg3",
    apiBasePath: "/api/views/isabella-heatmap",
  },
  {
    slug: "oliver-velez",
    username: "olvelez007",
    apiBasePath: "/api/views/oliver-velez-heatmap",
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
