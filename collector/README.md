# ModelInfo Collector

Automated AI model metadata collector. Scrapes official docs, APIs, and independent evaluation sources. Data stored in TursoDB. Runs on GitHub Actions cron.

## Quick Start

```bash
cd collector
pip install -e ".[dev]"

# Dry-run (fetch but don't write to DB)
python -m modelinfo.cli collect --table evaluations --source lmarena --dry-run

# Collect all data
python -m modelinfo.cli collect --table all --source all
```

## Setup

Set environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `TURSO_DB_URL` | For production | TursoDB connection URL |
| `TURSO_AUTH_TOKEN` | For production | TursoDB auth token |
| `AA_API_KEY` | For AA evaluations | Artificial Analysis API Key (free) |

For local testing, omit `TURSO_DB_URL` and `TURSO_AUTH_TOKEN` to use a local SQLite file.

## Commands

### collect

```bash
# Collect all data from all sources
python -m modelinfo.cli collect --table all --source all

# Collect only evaluations from a specific source
python -m modelinfo.cli collect --table evaluations --source lmarena
python -m modelinfo.cli collect --table evaluations --source artificialanalysis
python -m modelinfo.cli collect --table evaluations --source llmregistry

# Collect only pricing from OpenRouter
python -m modelinfo.cli collect --table pricing --source openrouter

# Dry-run (fetch but don't write to DB)
python -m modelinfo.cli collect --table models --dry-run
```

## Data Sources

### Model & Pricing Sources

| Source | Type | Coverage |
|--------|------|----------|
| OpenRouter | JSON API | 300+ models, pricing |
| OpenAI | HTML scrape | Official models + pricing |
| Anthropic | HTML scrape | Claude models + pricing |

### Evaluation Sources (Third-Party Independent Only)

| Source | Type | Coverage | Auth |
|--------|------|----------|------|
| Artificial Analysis | API v2 | 516 models | API Key required |
| LMArena (Chatbot Arena) | GitHub JSON | 282 models | Free, no auth |
| LLM Registry | API | 45 models (independent only) | Free, no auth |

### Evaluation Fields

**Artificial Analysis fields:** `aa_intelligence_index`, `aa_coding_index`, `aa_math_index`, `mmlu_pro`, `gpqa`, `hle`, `aime`, `livecodebench`, `scicode`, `ifbench`, `aa_lcr`, `tokens_per_second`, `ttft_ms`

**LMArena fields:** `lmarena_elo`, `lmarena_coding`, `lmarena_math`, `lmarena_hard`

## Project Structure

```
collector/
├── src/modelinfo/
│   ├── models.py         # Pydantic data models
│   ├── db.py             # TursoDB client + schema
│   ├── fetcher.py        # HTTP client with retry + custom headers
│   ├── normalizer.py     # Field normalization
│   ├── differ.py         # Change detection
│   ├── writer.py         # DB upsert with validation
│   ├── validator.py      # Data sanity checks
│   ├── change_log.py     # Change log + error tracking
│   ├── cli.py            # Typer CLI
│   └── parsers/
│       ├── base.py                # Abstract parser interface
│       ├── openrouter.py          # OpenRouter API parser
│       ├── openai.py              # OpenAI docs parser
│       ├── anthropic.py           # Anthropic docs parser
│       ├── artificialanalysis.py  # Artificial Analysis API parser
│       ├── lmarena.py             # LMArena leaderboard parser
│       └── llmregistry.py         # LLM Registry parser (independent only)
└── tests/
    ├── fixtures/         # Recorded HTML/JSON from real sources
    └── parsers/          # Parser unit tests
```

## Adding a New Source

1. Create parser in `src/modelinfo/parsers/` extending `BaseParser`
2. Implement `fetch_models()`, `fetch_pricing()`, and/or `fetch_evaluations()`
3. Register in `cli.py` `_get_sources()`
4. Add test fixtures and test file in `tests/parsers/`

## Automation

- **Daily**: Price check at 08:00 UTC (`.github/workflows/daily-price-check.yml`)
- **Weekly**: Full collect at 02:00 UTC Mondays (`.github/workflows/weekly-full-collect.yml`)
