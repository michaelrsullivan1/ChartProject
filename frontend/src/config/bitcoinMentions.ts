export type BitcoinMentionsDefinition = {
  slug: string;
  username: string;
};

export const bitcoinMentionsDefinitions: BitcoinMentionsDefinition[] = [
  {
    slug: "michael-saylor",
    username: "saylor",
  },
  {
    slug: "walker-america",
    username: "WalkerAmerica",
  },
  {
    slug: "chris-millas",
    username: "ChrisMMillas",
  },
  {
    slug: "richard-byworth",
    username: "RichardByworth",
  },
  {
    slug: "andrew-webley",
    username: "asjwebley",
  },
  {
    slug: "ray",
    username: "artificialsub",
  },
  {
    slug: "stack-hodler",
    username: "stackhodler",
  },
  {
    slug: "isabella",
    username: "isabellasg3",
  },
  {
    slug: "oliver-velez",
    username: "olvelez007",
  },
  {
    slug: "ben-werkman",
    username: "Werkman",
  },
  {
    slug: "brian-brookshire",
    username: "btc_overflow",
  },
  {
    slug: "brian-armstrong",
    username: "brian_armstrong",
  },
  {
    slug: "cz-bnb",
    username: "cz_binance",
  },
  {
    slug: "arthur-hayes",
    username: "CryptoHayes",
  },
  {
    slug: "jesse-powell",
    username: "jespow",
  },
  {
    slug: "jack-mallers",
    username: "jackmallers",
  },
  {
    slug: "zynx",
    username: "ZynxBTC",
  },
  {
    slug: "jesse-myers",
    username: "Croesus_BTC",
  },
  {
    slug: "willy-woo",
    username: "willywoo",
  },
  {
    slug: "andy-edstrom",
    username: "edstromandrew",
  },
  {
    slug: "dan-hillery",
    username: "hillery_dan",
  },
  {
    slug: "adrian-morris",
    username: "_Adrian",
  },
  {
    slug: "jeff-walton",
    username: "PunterJeff",
  },
  {
    slug: "nithu-sezni",
    username: "nithusezni",
  },
  {
    slug: "mason",
    username: "MasonFoard",
  },
  {
    slug: "michael-sullivan",
    username: "SullyMichaelvan",
  },
  {
    slug: "peter-schiff",
    username: "PeterSchiff",
  },
];

export function findBitcoinMentionsBySlug(
  slug: string,
): BitcoinMentionsDefinition | undefined {
  return bitcoinMentionsDefinitions.find((definition) => definition.slug === slug);
}

export function getBitcoinMentionsHash(slug: string): string {
  return `#/bitcoin-mentions/${slug}`;
}

export function getBitcoinMentionsLabel(
  definition: BitcoinMentionsDefinition,
): string {
  return definition.slug
    .split("-")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getBitcoinMentionsTitle(
  definition: BitcoinMentionsDefinition,
): string {
  return `${getBitcoinMentionsLabel(definition)} Bitcoin Mentions`;
}
