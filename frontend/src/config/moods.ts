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
    slug: "oliver-velez",
    username: "olvelez007",
    apiBasePath: "/api/views/oliver-velez-moods",
  },
  {
    slug: "ben-werkman",
    username: "Werkman",
    apiBasePath: "/api/views/ben-werkman-moods",
  },
  {
    slug: "brian-brookshire",
    username: "btc_overflow",
    apiBasePath: "/api/views/brian-brookshire-moods",
  },
  {
    slug: "brian-armstrong",
    username: "brian_armstrong",
    apiBasePath: "/api/views/brian-armstrong-moods",
  },
  {
    slug: "cz-bnb",
    username: "cz_binance",
    apiBasePath: "/api/views/cz-bnb-moods",
  },
  {
    slug: "arthur-hayes",
    username: "CryptoHayes",
    apiBasePath: "/api/views/arthur-hayes-moods",
  },
  {
    slug: "jesse-powell",
    username: "jespow",
    apiBasePath: "/api/views/jesse-powell-moods",
  },
  {
    slug: "jack-mallers",
    username: "jackmallers",
    apiBasePath: "/api/views/jack-mallers-moods",
  },
  {
    slug: "zynx",
    username: "ZynxBTC",
    apiBasePath: "/api/views/zynx-moods",
  },
  {
    slug: "jesse-myers",
    username: "Croesus_BTC",
    apiBasePath: "/api/views/jesse-myers-moods",
  },
  {
    slug: "willy-woo",
    username: "willywoo",
    apiBasePath: "/api/views/willy-woo-moods",
  },
  {
    slug: "andy-edstrom",
    username: "edstromandrew",
    apiBasePath: "/api/views/andy-edstrom-moods",
  },
  {
    slug: "dan-hillery",
    username: "hillery_dan",
    apiBasePath: "/api/views/dan-hillery-moods",
  },
  {
    slug: "adrian-morris",
    username: "_Adrian",
    apiBasePath: "/api/views/adrian-morris-moods",
  },
  {
    slug: "jeff-walton",
    username: "PunterJeff",
    apiBasePath: "/api/views/jeff-walton-moods",
  },
  {
    slug: "nithu-sezni",
    username: "nithusezni",
    apiBasePath: "/api/views/nithu-sezni-moods",
  },
  {
    slug: "mason",
    username: "MasonFoard",
    apiBasePath: "/api/views/mason-moods",
  },
  {
    slug: "british-hodl",
    username: "BritishHodl",
    apiBasePath: "/api/views/british-hodl-moods",
  },
  {
    slug: "lyn-alden",
    username: "LynAldenContact",
    apiBasePath: "/api/views/lyn-alden-moods",
  },
  {
    slug: "professor-b21",
    username: "ProfessorB21",
    apiBasePath: "/api/views/professor-b21-moods",
  },
  {
    slug: "btc-gus",
    username: "Scavacini777",
    apiBasePath: "/api/views/btc-gus-moods",
  },
  {
    slug: "bit-paine",
    username: "BitPaine",
    apiBasePath: "/api/views/bit-paine-moods",
  },
  {
    slug: "matt-cole",
    username: "ColeMacro",
    apiBasePath: "/api/views/matt-cole-moods",
  },
  {
    slug: "parker-lewis",
    username: "parkeralewis",
    apiBasePath: "/api/views/parker-lewis-moods",
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
