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
    slug: "andrew-webley",
    username: "asjwebley",
    apiBasePath: "/api/views/andrew-webley-overview",
  },
  {
    slug: "ray",
    username: "artificialsub",
    apiBasePath: "/api/views/ray-overview",
  },
  {
    slug: "stack-hodler",
    username: "stackhodler",
    apiBasePath: "/api/views/stack-hodler-overview",
  },
  {
    slug: "isabella",
    username: "isabellasg3",
    apiBasePath: "/api/views/isabella-overview",
  },
  {
    slug: "oliver-velez",
    username: "olvelez007",
    apiBasePath: "/api/views/oliver-velez-overview",
  },
  {
    slug: "ben-werkman",
    username: "Werkman",
    apiBasePath: "/api/views/ben-werkman-overview",
  },
  {
    slug: "brian-brookshire",
    username: "btc_overflow",
    apiBasePath: "/api/views/brian-brookshire-overview",
  },
  {
    slug: "brian-armstrong",
    username: "brian_armstrong",
    apiBasePath: "/api/views/brian-armstrong-overview",
  },
  {
    slug: "cz-bnb",
    username: "cz_binance",
    apiBasePath: "/api/views/cz-bnb-overview",
  },
  {
    slug: "arthur-hayes",
    username: "CryptoHayes",
    apiBasePath: "/api/views/arthur-hayes-overview",
  },
  {
    slug: "jesse-powell",
    username: "jespow",
    apiBasePath: "/api/views/jesse-powell-overview",
  },
  {
    slug: "jack-mallers",
    username: "jackmallers",
    apiBasePath: "/api/views/jack-mallers-overview",
  },
  {
    slug: "zynx",
    username: "ZynxBTC",
    apiBasePath: "/api/views/zynx-overview",
  },
  {
    slug: "jesse-myers",
    username: "Croesus_BTC",
    apiBasePath: "/api/views/jesse-myers-overview",
  },
  {
    slug: "willy-woo",
    username: "willywoo",
    apiBasePath: "/api/views/willy-woo-overview",
  },
  {
    slug: "andy-edstrom",
    username: "edstromandrew",
    apiBasePath: "/api/views/andy-edstrom-overview",
  },
  {
    slug: "dan-hillery",
    username: "hillery_dan",
    apiBasePath: "/api/views/dan-hillery-overview",
  },
  {
    slug: "adrian-morris",
    username: "_Adrian",
    apiBasePath: "/api/views/adrian-morris-overview",
  },
  {
    slug: "jeff-walton",
    username: "PunterJeff",
    apiBasePath: "/api/views/jeff-walton-overview",
  },
  {
    slug: "nithu-sezni",
    username: "nithusezni",
    apiBasePath: "/api/views/nithu-sezni-overview",
  },
  {
    slug: "mason",
    username: "MasonFoard",
    apiBasePath: "/api/views/mason-overview",
  },
  {
    slug: "british-hodl",
    username: "BritishHodl",
    apiBasePath: "/api/views/british-hodl-overview",
  },
  {
    slug: "lyn-alden",
    username: "LynAldenContact",
    apiBasePath: "/api/views/lyn-alden-overview",
  },
  {
    slug: "professor-b21",
    username: "ProfessorB21",
    apiBasePath: "/api/views/professor-b21-overview",
  },
  {
    slug: "btc-gus",
    username: "Scavacini777",
    apiBasePath: "/api/views/btc-gus-overview",
  },
  {
    slug: "bit-paine",
    username: "BitPaine",
    apiBasePath: "/api/views/bit-paine-overview",
  },
  {
    slug: "matt-cole",
    username: "ColeMacro",
    apiBasePath: "/api/views/matt-cole-overview",
  },
  {
    slug: "parker-lewis",
    username: "parkeralewis",
    apiBasePath: "/api/views/parker-lewis-overview",
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
