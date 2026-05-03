function range(start: number, end: number, step: number): number[] {
  const values: number[] = [];
  for (let current = start; current <= end; current += step) {
    values.push(current);
  }
  return values;
}

export const PRICE_MENTION_BUCKETS = [
  ...range(10_000, 100_000, 10_000),
  ...range(125_000, 250_000, 25_000),
  ...range(300_000, 500_000, 50_000),
  ...range(600_000, 1_000_000, 100_000),
  ...range(1_250_000, 2_000_000, 250_000),
];
