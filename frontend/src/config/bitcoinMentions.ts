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
