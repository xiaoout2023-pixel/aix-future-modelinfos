# ModelInfo Collector

Automated AI model metadata collector. Scrapes official docs, OpenRouter, and eval sites.
Data stored in TursoDB. Runs on GitHub Actions cron.

## Quick Start

```bash
cd collector
pip install -e ".[dev]"
python -m modelinfo.cli collect all --dry-run
```

## Setup

Set environment variables:
- `TURSO_DB_URL`: TursoDB connection URL
- `TURSO_AUTH_TOKEN`: TursoDB auth token

For local testing, omit both to use a local SQLite file.

## Commands

### collect

```bash
# Collect all data from all sources
python -m modelinfo.cli collect all

# Collect only pricing from OpenRouter
python -m modelinfo.cli collect pricing --source openrouter

# Dry-run (fetch but don't write to DB)
python -m modelinfo.cli collect models --dry-run

# Collect from a specific source
python -m modelinfo.cli collect all --source openai
```

### diff

```bash
python -m modelinfo.cli diff --dry-run
```

## Data Sources

| Source | Type | Coverage |
|--------|------|----------|
| OpenRouter | JSON API | 300+ models, pricing |
| OpenAI | HTML scrape | Official models + pricing |
| Anthropic | HTML scrape | Claude models + pricing |

## Project Structure

```
collector/
├── src/modelinfo/
│   ├── models.py         # Pydantic data models
│   ├── db.py             # TursoDB client
│   ├── fetcher.py        # HTTP client with retry
│   ├── normalizer.py     # Field normalization
│   ├── differ.py         # Change detection
│   ├── writer.py         # DB upsert with validation
│   ├── validator.py      # Data sanity checks
│   ├── change_log.py     # Change log + error tracking
│   ├── cli.py            # Typer CLI
│   └── parsers/
│       ├── base.py       # Abstract parser interface
│       ├── openrouter.py # OpenRouter API parser
│       ├── openai.py     # OpenAI docs parser
│       └── anthropic.py  # Anthropic docs parser
└── tests/
    ├── fixtures/         # Recorded HTML/JSON from real sources
    └── ...               # Test files
```

## Adding a New Source

1. Create parser in `src/modelinfo/parsers/` extending `BaseParser`
2. Implement `fetch_models()` and `fetch_pricing()`
3. Register in `cli.py` `_get_sources()`
4. Add test fixtures and test file in `tests/parsers/`

## Automation

- **Daily**: Price check at 08:00 UTC (`.github/workflows/daily-price-check.yml`)
- **Weekly**: Full collect at 02:00 UTC Mondays (`.github/workflows/weekly-full-collect.yml`)
