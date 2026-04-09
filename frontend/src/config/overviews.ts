export type OverviewDefinition = {
  slug: string;
  username: string;
  apiBasePath: string;
};

export const overviewDefinitions: OverviewDefinition[] = [
  {
    slug: "michael-saylor",
    username: "saylor",
    apiBasePath: "/api/views/michael-saylor-overview",
  },
  {
    slug: "walker-america",
    username: "WalkerAmerica",
    apiBasePath: "/api/views/walker-america-overview",
  },
  {
    slug: "chris-millas",
    username: "ChrisMMillas",
    apiBasePath: "/api/views/chris-millas-overview",
  },
  {
    slug: "richard-byworth",
    username: "RichardByworth",
    apiBasePath: "/api/views/richard-byworth-overview",
  },
  {
    slug: "michael-sullivan",
    username: "SullyMichaelvan",
    apiBasePath: "/api/views/michael-sullivan-overview",
  },
  {
    slug: "peter-schiff",
    username: "PeterSchiff",
    apiBasePath: "/api/views/peter-schiff-overview",
  },
];

export function findOverviewBySlug(slug: string): OverviewDefinition | undefined {
  return overviewDefinitions.find((overview) => overview.slug === slug);
}

export function getOverviewHash(slug: string): string {
  return `#/overviews/${slug}`;
}

export function getOverviewLabel(overview: OverviewDefinition): string {
  return overview.slug
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getOverviewTitle(overview: OverviewDefinition): string {
  return `${getOverviewLabel(overview)} Overview`;
}
