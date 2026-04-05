const aggregateMoodLabels = [
  "admiration",
  "amusement",
  "anger",
  "annoyance",
  "approval",
  "caring",
  "confusion",
  "curiosity",
  "desire",
  "disappointment",
  "disapproval",
  "disgust",
  "embarrassment",
  "excitement",
  "fear",
  "gratitude",
  "grief",
  "joy",
  "love",
  "nervousness",
  "neutral",
  "optimism",
  "pride",
  "realization",
  "relief",
  "remorse",
  "sadness",
  "surprise",
] as const;

export type AggregateMoodDefinition = {
  slug: string;
  moodLabel: string;
  apiBasePath: string;
};

const aggregateMoodDescriptions: Record<string, string> = {
  admiration: "Respect, praise, or appreciation directed toward someone or something.",
  amusement: "A sense of finding something funny, playful, or entertaining.",
  anger: "Strong displeasure, hostility, or frustration in response to a perceived wrong.",
  annoyance: "Mild irritation or frustration, usually lower intensity than anger.",
  approval: "Agreement, endorsement, or positive evaluation of a person, action, or idea.",
  caring: "Warm concern, support, or protectiveness toward someone else.",
  confusion: "Uncertainty or difficulty understanding what is happening or being said.",
  curiosity: "Interest and desire to learn more or explore further details.",
  desire: "Wanting or longing for an outcome, object, or experience.",
  disappointment: "Feeling let down when expectations are not met.",
  disapproval: "Negative judgment or criticism of behavior, decisions, or ideas.",
  disgust: "Revulsion or strong aversion toward something considered offensive or unpleasant.",
  embarrassment: "Self-conscious discomfort from perceived social awkwardness or exposure.",
  excitement: "High-energy anticipation, enthusiasm, or elevated positive arousal.",
  fear: "Sense of threat, danger, or concern about potential harm or loss.",
  gratitude: "Thankfulness and appreciation for help, value, or positive outcomes.",
  grief: "Deep sorrow linked to loss, absence, or emotional pain.",
  joy: "Strong happiness, delight, or emotional uplift.",
  love: "Deep affection, attachment, or emotional closeness.",
  nervousness: "Tension or anxious unease about uncertainty or upcoming events.",
  neutral: "No strong emotional signal; informational, factual, or emotionally flat language.",
  optimism: "Expectation that outcomes will improve or turn out well.",
  pride: "Positive self-regard from achievement, identity, or valued association.",
  realization: "Recognition or sudden understanding of something previously unclear.",
  relief: "Release of stress after danger, uncertainty, or pressure passes.",
  remorse: "Regret and self-blame over a perceived mistake or harm caused.",
  sadness: "Low-arousal negative affect linked to loss, hurt, or discouragement.",
  surprise: "Reaction to something unexpected, without fixed positive or negative direction.",
};

export const aggregateMoodDefinitions: AggregateMoodDefinition[] = aggregateMoodLabels.map(
  (moodLabel) => ({
    slug: moodLabel.replace(/_/g, "-"),
    moodLabel,
    apiBasePath: "/api/views/aggregate-moods",
  }),
);

export function findAggregateMoodBySlug(slug: string): AggregateMoodDefinition | undefined {
  return aggregateMoodDefinitions.find((definition) => definition.slug === slug);
}

export function getAggregateMoodHash(slug: string): string {
  return `#/aggregate-moods/${slug}`;
}

export function getAggregateMoodLabel(definition: AggregateMoodDefinition): string {
  return definition.moodLabel
    .split("_")
    .filter(Boolean)
    .map((segment) => segment.charAt(0).toUpperCase() + segment.slice(1))
    .join(" ");
}

export function getAggregateMoodTitle(definition: AggregateMoodDefinition): string {
  return `Aggregate ${getAggregateMoodLabel(definition)}`;
}

export function getMoodDescriptionByLabel(moodLabel: string): string {
  return (
    aggregateMoodDescriptions[moodLabel] ??
    "Emotion label from the GoEmotions taxonomy used by the active model."
  );
}

export function getAggregateMoodDescription(definition: AggregateMoodDefinition): string {
  return getMoodDescriptionByLabel(definition.moodLabel);
}
