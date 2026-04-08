export const themeDefinitions = [
  {
    slug: "slate",
    label: "Slate Blue",
    description: "Crisp navy surfaces with cool blue highlights.",
  },
  {
    slug: "graphite",
    label: "Graphite Ice",
    description: "Neutral graphite base with restrained steel-blue accents.",
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
