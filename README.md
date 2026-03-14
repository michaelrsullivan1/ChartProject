# ChartProject

A reusable data + visualization foundation for historical timeline visualizations.

This repo is structured to support multiple future visualizations while staying pragmatic:
- shared ingestion/storage/time-series tooling in `core/` and `domains/`
- project-specific composition in `projects/`
- immutable raw data separate from transformed and rendered outputs

## Current Status (Chunk 3)
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
- social ingestion source abstraction
- Michael Saylor ingestion pipeline via X API v2 with pagination + checkpoint resume + dedupe

Not implemented yet:
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
    ingest_saylor_posts.py
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

## Social Pipeline (Chunk 3)

Set X API bearer token in `.env`:

```bash
X_API_BEARER_TOKEN=your_token_here
```

### X Website Setup Checklist

1. Sign in at [developer portal](https://developer.x.com/en/portal/dashboard).
2. Create a Project (or open an existing one).
3. Create an App inside that Project.
4. In App settings, ensure permissions include **Read** access.
5. In App keys/tokens, generate a **Bearer Token**.
6. Put that token in your local `.env` as `X_API_BEARER_TOKEN=...`.
7. Verify credentials and endpoint access from this repo:

```bash
python3 scripts/check_x_api_setup.py --username saylor
```

If this succeeds, run full ingestion.

Run ingestion:

```bash
python3 scripts/ingest_saylor_posts.py --username saylor
```

Key behavior:
- paginated ingestion from X API v2 user posts endpoint
- checkpoint resume state in `data/interim/social/<username>_x_api_checkpoint.json`
- raw page payload archive in `data/raw/social/`
- idempotent upsert/dedupe into `raw_social_posts`

Optional controls:
- `--max-pages 2` to test with a limited pull
- `--no-resume` to ignore checkpoint and start fresh

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

## Social Source Note

The first concrete social source uses X API v2 and requires a bearer token.
The ingestion layer is source-abstracted so alternate providers can be added later without changing downstream tables.

## Next Chunk

Chunk 4 will implement rule-based Bitcoin-related classification (inspectable + override-friendly).
