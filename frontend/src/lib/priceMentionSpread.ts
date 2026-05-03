import type { PriceMentionPeriod } from "../api/priceMentions";

export const MIN_PRICE_SPREAD_VISIBLE_MENTIONS = 4;
export const MIN_PRICE_SPREAD_STRONG_MENTIONS = 8;

export type PriceSpreadSampleStrength = "insufficient" | "weak" | "strong";

export type PriceMentionSpreadPeriod = {
  periodStart: string;
  btcClose: number | null;
  predictionCount: number;
  sampleStrength: PriceSpreadSampleStrength;
  medianPrice: number | null;
  q25Price: number | null;
  q75Price: number | null;
  medianPremiumPct: number | null;
  spreadPct: number | null;
};

export function derivePriceMentionSpreadPeriods(
  periods: PriceMentionPeriod[],
): PriceMentionSpreadPeriod[] {
  return periods.map((period) => {
    const btcClose = period.btc_close;
    const weightedMentions = period.mentions
      .filter((mention) => mention.count > 0 && mention.price_usd > 0)
      .map((mention) => ({
        priceUsd: mention.price_usd,
        weight: mention.count,
      }));
    const predictionCount = weightedMentions.reduce((total, mention) => total + mention.weight, 0);

    if (
      btcClose === null ||
      btcClose <= 0 ||
      predictionCount < MIN_PRICE_SPREAD_VISIBLE_MENTIONS ||
      weightedMentions.length === 0
    ) {
      return {
        periodStart: period.period_start,
        btcClose,
        predictionCount,
        sampleStrength: "insufficient",
        medianPrice: null,
        q25Price: null,
        q75Price: null,
        medianPremiumPct: null,
        spreadPct: null,
      };
    }

    const weightedLogRatios = weightedMentions
      .map((mention) => ({
        value: Math.log(mention.priceUsd / btcClose),
        weight: mention.weight,
      }))
      .sort((left, right) => left.value - right.value);

    const q25LogRatio = weightedQuantile(weightedLogRatios, 0.25);
    const medianLogRatio = weightedQuantile(weightedLogRatios, 0.5);
    const q75LogRatio = weightedQuantile(weightedLogRatios, 0.75);

    const q25Price = btcClose * Math.exp(q25LogRatio);
    const medianPrice = btcClose * Math.exp(medianLogRatio);
    const q75Price = btcClose * Math.exp(q75LogRatio);

    return {
      periodStart: period.period_start,
      btcClose,
      predictionCount,
      sampleStrength:
        predictionCount >= MIN_PRICE_SPREAD_STRONG_MENTIONS ? "strong" : "weak",
      medianPrice,
      q25Price,
      q75Price,
      medianPremiumPct: (Math.exp(medianLogRatio) - 1) * 100,
      spreadPct: ((q75Price - q25Price) / btcClose) * 100,
    };
  });
}

function weightedQuantile(
  weightedValues: Array<{ value: number; weight: number }>,
  quantile: number,
): number {
  if (weightedValues.length === 0) {
    return 0;
  }

  const totalWeight = weightedValues.reduce((sum, item) => sum + item.weight, 0);
  if (totalWeight <= 0) {
    return weightedValues[weightedValues.length - 1]?.value ?? 0;
  }

  const targetWeight = totalWeight * quantile;
  let cumulativeWeight = 0;

  for (const item of weightedValues) {
    cumulativeWeight += item.weight;
    if (cumulativeWeight >= targetWeight) {
      return item.value;
    }
  }

  return weightedValues[weightedValues.length - 1]?.value ?? 0;
}
