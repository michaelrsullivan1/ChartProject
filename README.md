# ChartProject

A reusable data + visualization foundation for historical timeline visualizations.

This repo is structured to support multiple future visualizations while staying pragmatic:
- shared ingestion/storage/time-series tooling in `core/` and `domains/`
- project-specific composition in `projects/`
- immutable raw data separate from transformed and rendered outputs

## Current Status (Chunk 2)
Implemented:
- Python project scaffold (`pyproject.toml`, `Makefile`, env template)
- directory layout for raw/interim/processed/manual/output data
- central config and logging setup
- DuckDB warehouse bootstrap
- initial data model tables for social posts, BTC prices, aggregates, and aligned series
- schema validation script
- starter tests
- BTC ingestion pipeline (daily candles)
- BTC weekly/monthly aggregation pipeline

Not implemented yet:
- Saylor post ingestion
- classification pipeline
- aggregation/alignment transforms
- visualization rendering

## Repository Layout

```text
ChartProject/
  data/
    raw/                # immutable source pulls
      social/
      market/
    interim/            # intermediate transformations
    processed/          # analysis-ready outputs
    manual/             # human-curated files (tracked)
    warehouse/          # DuckDB analytics database
  notebooks/
  output/
    charts/
    animations/
    cards/
  scripts/
    bootstrap_project.py
    validate_schemas.py
    ingest_btc_prices.py
    aggregate_btc_prices.py
  src/chartproject/
    core/               # config, logging, storage, schema registry
    domains/
      social/           # reusable social dataset schemas/pipelines
      market/           # reusable market dataset schemas/pipelines
    projects/
      saylor_btc/       # project-specific tables/orchestration
  tests/
```

## Data Model (Initial)

### Social domain
- `raw_social_posts`
- `classified_social_posts`
- `social_post_aggregates`

### Market domain
- `raw_btc_prices`
- `btc_price_aggregates`

### Project-specific (Saylor x BTC)
- `manual_iconic_events`
- `aligned_saylor_btc_series`

## Quick Start

1. Install dependencies:

```bash
make install
```

2. Optional env config:

```bash
cp .env.example .env
```

3. Bootstrap folders + DuckDB schema:

```bash
make bootstrap
```

4. Validate schema contract:

```bash
make validate-schemas
```

5. Run tests:

```bash
make test
```

## BTC Pipeline (Chunk 2)

1. Pull BTC daily data and load warehouse:

```bash
python3 scripts/ingest_btc_prices.py
```

2. Build weekly/monthly aggregate candles:

```bash
python3 scripts/aggregate_btc_prices.py
```

Outputs:
- raw source snapshots: `data/raw/market/`
- normalized daily parquet: `data/processed/market/btc_usd_daily_stooq.parquet`
- warehouse tables: `raw_btc_prices`, `btc_price_aggregates`

## Configuration

Environment variables:
- `PROJECT_TIMEZONE` (default `UTC`)
- `LOG_LEVEL` (default `INFO`)
- `DEFAULT_GRANULARITY` (default `monthly`)
- `X_API_BEARER_TOKEN` (for future social ingestion)
- `COINGECKO_API_KEY` (optional for future market ingestion)

## Why DuckDB + Parquet

This project uses DuckDB as the local analytics layer because it keeps joins and time-series analysis fast and simple across future datasets.
Parquet will be used for durable domain exports where portability matters.

## BTC Source Note

Default BTC source is `stooq` because it provides long-range daily OHLC history without API keys.
CoinGecko public access is now limited for deep historical range queries, so it is not the default ingestion source for this project baseline.

## Next Chunk

Chunk 3 will implement Michael Saylor post ingestion with source abstraction, normalization, and resumable persistence.
