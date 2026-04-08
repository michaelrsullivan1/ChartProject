export const themeDefinitions = [
  {
    slug: "obsidian",
    label: "Obsidian Cyan",
    description: "High-contrast blackened graphite with precise cyan accents.",
  },
  {
    slug: "graphite",
    label: "Graphite Ice",
    description: "Neutral graphite base with restrained steel-blue accents.",
  },
  {
    slug: "slate",
    label: "Slate Blue",
    description: "Crisp navy surfaces with cool blue highlights.",
  },
  {
    slug: "midnight",
    label: "Midnight Cobalt",
    description: "Dense midnight surfaces with premium cobalt highlights.",
  },
  {
    slug: "evergreen",
    label: "Evergreen Mint",
    description: "Deep charcoal base with modern teal focus states.",
  },
] as const;

export type ThemeDefinition = (typeof themeDefinitions)[number];
export type ThemeSlug = ThemeDefinition["slug"];

export function isThemeSlug(value: string): value is ThemeSlug {
  return themeDefinitions.some((theme) => theme.slug === value);
}
