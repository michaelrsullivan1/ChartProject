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
    slug: "ben-werkman",
    username: "Werkman",
    apiBasePath: "/api/views/ben-werkman-heatmap",
  },
  {
    slug: "brian-brookshire",
    username: "btc_overflow",
    apiBasePath: "/api/views/brian-brookshire-heatmap",
  },
  {
    slug: "brian-armstrong",
    username: "brian_armstrong",
    apiBasePath: "/api/views/brian-armstrong-heatmap",
  },
  {
    slug: "cz-bnb",
    username: "cz_binance",
    apiBasePath: "/api/views/cz-bnb-heatmap",
  },
  {
    slug: "arthur-hayes",
    username: "CryptoHayes",
    apiBasePath: "/api/views/arthur-hayes-heatmap",
  },
  {
    slug: "jesse-powell",
    username: "jespow",
    apiBasePath: "/api/views/jesse-powell-heatmap",
  },
  {
    slug: "jack-mallers",
    username: "jackmallers",
    apiBasePath: "/api/views/jack-mallers-heatmap",
  },
  {
    slug: "zynx",
    username: "ZynxBTC",
    apiBasePath: "/api/views/zynx-heatmap",
  },
  {
    slug: "jesse-myers",
    username: "Croesus_BTC",
    apiBasePath: "/api/views/jesse-myers-heatmap",
  },
  {
    slug: "willy-woo",
    username: "willywoo",
    apiBasePath: "/api/views/willy-woo-heatmap",
  },
  {
    slug: "andy-edstrom",
    username: "edstromandrew",
    apiBasePath: "/api/views/andy-edstrom-heatmap",
  },
  {
    slug: "dan-hillery",
    username: "hillery_dan",
    apiBasePath: "/api/views/dan-hillery-heatmap",
  },
  {
    slug: "adrian-morris",
    username: "_Adrian",
    apiBasePath: "/api/views/adrian-morris-heatmap",
  },
  {
    slug: "jeff-walton",
    username: "PunterJeff",
    apiBasePath: "/api/views/jeff-walton-heatmap",
  },
  {
    slug: "nithu-sezni",
    username: "nithusezni",
    apiBasePath: "/api/views/nithu-sezni-heatmap",
  },
  {
    slug: "mason",
    username: "MasonFoard",
    apiBasePath: "/api/views/mason-heatmap",
  },
  {
    slug: "british-hodl",
    username: "BritishHodl",
    apiBasePath: "/api/views/british-hodl-heatmap",
  },
  {
    slug: "lyn-alden",
    username: "LynAldenContact",
    apiBasePath: "/api/views/lyn-alden-heatmap",
  },
  {
    slug: "professor-b21",
    username: "ProfessorB21",
    apiBasePath: "/api/views/professor-b21-heatmap",
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
