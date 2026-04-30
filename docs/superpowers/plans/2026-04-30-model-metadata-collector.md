# Model Metadata Collector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated AI model metadata collector that scrapes official docs + OpenRouter + eval sites, normalizes the data, diffs against existing TursoDB records, and writes changes. Runs on GitHub Actions cron schedule.

**Architecture:** Python CLI (typer) with async HTTP fetching (httpx), per-source parsers producing Pydantic models, a normalization/diff/write pipeline, and TursoDB as the backing store. Tests use recorded fixtures (no live network).

**Tech Stack:** Python 3.12+, httpx, beautifulsoup4+lxml, pydantic v2, libsql-client, typer, pytest + pytest-httpx + pytest-asyncio, structlog

---

### Task 1: Project scaffold + Pydantic data models

**Files:**
- Create: `collector/pyproject.toml`
- Create: `collector/src/modelinfo/__init__.py`
- Create: `collector/src/modelinfo/models.py`
- Create: `collector/tests/__init__.py`
- Create: `collector/tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# collector/tests/test_models.py
from datetime import date
from modelinfo.models import ModelInfo, PricingInfo, Capabilities, Urls, Channel

def test_model_info_minimal():
    m = ModelInfo(model_id="openai/gpt-4o", model_name="GPT-4o", provider="openai")
    assert m.model_id == "openai/gpt-4o"
    assert m.capabilities.text is False
    assert m.tags == []

def test_model_info_full():
    m = ModelInfo(
        model_id="anthropic/claude-sonnet-4-6",
        model_name="Claude Sonnet 4.6",
        provider="anthropic",
        provider_type="closed",
        release_date=date(2025, 6, 15),
        aliases=["claude-sonnet-4-6-20250615"],
        capabilities=Capabilities(text=True, code=True, reasoning=True, vision=True, tool_use=True),
        context_length=200000,
        max_output_tokens=8192,
        urls=Urls(official="https://anthropic.com/claude", pricing="https://anthropic.com/pricing"),
    )
    assert m.capabilities.text is True
    assert m.capabilities.video is False
    assert m.context_length == 200000

def test_pricing_info():
    p = PricingInfo(
        pricing_id="openai/gpt-4o/official/global/2025-01-01",
        model_id="openai/gpt-4o",
        channel=Channel.OFFICIAL,
        valid_from=date(2025, 1, 1),
        input_price_per_1m=2.5,
        output_price_per_1m=10.0,
    )
    assert p.input_price_per_1m == 2.5
    assert p.cache_read_price_per_1m is None

def test_capabilities_default_false():
    c = Capabilities()
    assert c.text is False
    assert c.video is False
    assert c.embedding is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd collector && python -m pytest tests/test_models.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Create project scaffold**

```toml
# collector/pyproject.toml
[project]
name = "modelinfo-collector"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "httpx>=0.28",
    "beautifulsoup4>=4.12",
    "lxml>=5.3",
    "pydantic>=2.10",
    "libsql-client>=0.5",
    "typer>=0.15",
    "structlog>=24.4",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-httpx>=0.32",
    "pytest-asyncio>=0.24",
]

[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

```python
# collector/src/modelinfo/__init__.py
"""Model metadata collector - scrapes and normalizes AI model metadata."""
```

- [ ] **Step 4: Write Pydantic models**

```python
# collector/src/modelinfo/models.py
from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProviderType(str, Enum):
    OPEN_SOURCE = "open_source"
    CLOSED = "closed"


class ModelStatus(str, Enum):
    ACTIVE = "active"
    BETA = "beta"
    DEPRECATED = "deprecated"
    COMING_SOON = "coming_soon"


class Channel(str, Enum):
    OFFICIAL = "official"
    MARKETPLACE = "marketplace"
    RESELLER = "reseller"


class ReasoningLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Capabilities(BaseModel):
    text: bool = False
    code: bool = False
    reasoning: bool = False
    vision: bool = False
    image_gen: bool = False
    audio: bool = False
    audio_gen: bool = False
    video: bool = False
    tool_use: bool = False
    structured_output: bool = False
    streaming: bool = False
    batch: bool = False
    fine_tuning: bool = False
    embedding: bool = False


class Urls(BaseModel):
    official: Optional[str] = None
    docs: Optional[str] = None
    pricing: Optional[str] = None


class ModelInfo(BaseModel):
    model_id: str
    model_name: str
    provider: str
    provider_type: Optional[ProviderType] = None
    release_date: Optional[date] = None
    status: ModelStatus = ModelStatus.ACTIVE
    aliases: list[str] = Field(default_factory=list)
    capabilities: Capabilities = Field(default_factory=Capabilities)
    context_length: Optional[int] = None
    max_output_tokens: Optional[int] = None
    regions: list[str] = Field(default_factory=list)
    private_deployment: bool = False
    openai_compatible: bool = False
    urls: Urls = Field(default_factory=Urls)
    tags: list[str] = Field(default_factory=list)
    last_updated: Optional[datetime] = None


class PricingInfo(BaseModel):
    pricing_id: str
    model_id: str
    channel: Channel = Channel.OFFICIAL
    market_name: Optional[str] = None
    region: str = "global"
    valid_from: date
    currency: str = "USD"
    input_price_per_1m: Optional[float] = None
    output_price_per_1m: Optional[float] = None
    cache_read_price_per_1m: Optional[float] = None
    cache_write_price_per_1m: Optional[float] = None
    reasoning_tokens_charged: bool = False
    reasoning_overhead_ratio: Optional[float] = None
    price_per_request: Optional[float] = None
    price_per_image: Optional[float] = None
    price_per_audio_min: Optional[float] = None
    tiers: Optional[dict] = None
    volume_discount: Optional[dict] = None
    reserved_discount_pct: Optional[float] = None
    free_tier_tokens: Optional[int] = None
    min_billable_tokens: Optional[int] = None
    rounding_unit: Optional[int] = None
    has_spot: bool = False
    source: Optional[str] = None
    last_verified: Optional[datetime] = None


class EvalInfo(BaseModel):
    eval_id: str
    model_id: str
    eval_date: date
    source: str
    mmlu: Optional[float] = None
    gsm8k: Optional[float] = None
    humaneval: Optional[float] = None
    other_benchmarks: Optional[dict] = None
    tokens_per_second: Optional[int] = None
    avg_latency_ms: Optional[int] = None
    p95_latency_ms: Optional[int] = None
    reasoning_level: Optional[ReasoningLevel] = None
    overall_score: Optional[float] = None
    cost_efficiency_score: Optional[float] = None


class ChangeRecord(BaseModel):
    table_name: str
    model_id: str
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    changed_at: datetime = Field(default_factory=datetime.now)
    source_url: Optional[str] = None
```

- [ ] **Step 5: Install dependencies and run tests**

Run: `cd collector && pip install -e ".[dev]" && python -m pytest tests/test_models.py -v`
Expected: 4 tests PASS

- [ ] **Step 6: Commit**

```bash
cd collector && git init && git add -A && git commit -m "feat: project scaffold with Pydantic data models"
```


### Task 2: Test fixtures — record real source data

**Files:**
- Create: `collector/tests/conftest.py`
- Create: `collector/tests/fixtures/openrouter_models.json`
- Create: `collector/tests/fixtures/openai_models_page.html`
- Create: `collector/tests/fixtures/openai_pricing_page.html`
- Create: `collector/tests/fixtures/anthropic_models_page.html`
- Create: `collector/tests/fixtures/anthropic_pricing_page.html`

- [ ] **Step 1: Create conftest with fixture loader**

```python
# collector/tests/conftest.py
import json
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def load_fixture_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def openrouter_response():
    return load_fixture_json("openrouter_models.json")


@pytest.fixture
def openai_models_html():
    return load_fixture("openai_models_page.html")


@pytest.fixture
def openai_pricing_html():
    return load_fixture("openai_pricing_page.html")


@pytest.fixture
def anthropic_models_html():
    return load_fixture("anthropic_models_page.html")


@pytest.fixture
def anthropic_pricing_html():
    return load_fixture("anthropic_pricing_page.html")
```

- [ ] **Step 2: Record real responses into fixture files**

```json
// collector/tests/fixtures/openrouter_models.json
// Go to https://openrouter.ai/api/v1/models and save the JSON response.
// For the test fixture, keep only 3 models to keep it small.
{
  "data": [
    {
      "id": "openai/gpt-4o",
      "name": "OpenAI: GPT-4o",
      "created": 1715360000,
      "description": "GPT-4o is OpenAI's multimodal flagship model.",
      "context_length": 128000,
      "architecture": { "modality": "text+image->text" },
      "pricing": {
        "prompt": "0.0000025",
        "completion": "0.00001",
        "image": "0.003125"
      },
      "top_provider": { "max_completion_tokens": 16384 }
    },
    {
      "id": "anthropic/claude-sonnet-4-6",
      "name": "Anthropic: Claude Sonnet 4.6",
      "created": 1749000000,
      "description": "Claude Sonnet 4.6 by Anthropic.",
      "context_length": 200000,
      "architecture": { "modality": "text+image->text" },
      "pricing": {
        "prompt": "0.000003",
        "completion": "0.000015",
        "image": null
      },
      "top_provider": { "max_completion_tokens": 8192 }
    },
    {
      "id": "google/gemini-2.5-flash",
      "name": "Google: Gemini 2.5 Flash",
      "created": 1745000000,
      "description": "Gemini 2.5 Flash by Google.",
      "context_length": 1048576,
      "architecture": { "modality": "text+image->text" },
      "pricing": { "prompt": "0.00000015", "completion": "0.0000006" },
      "top_provider": { "max_completion_tokens": 8192 }
    }
  ]
}
```

```html
<!-- collector/tests/fixtures/openai_models_page.html -->
<!-- Save a stripped copy of https://platform.openai.com/docs/models -->
<!-- Keep only the models table portion -->
<table>
<tr><th>Model</th><th>Description</th><th>Context window</th><th>Max output tokens</th></tr>
<tr><td>gpt-4o</td><td>Multimodal flagship model</td><td>128,000</td><td>16,384</td></tr>
<tr><td>gpt-4o-mini</td><td>Smaller, faster, cheaper</td><td>128,000</td><td>16,384</td></tr>
</table>
```

```html
<!-- collector/tests/fixtures/openai_pricing_page.html -->
<!-- Save a stripped copy of https://platform.openai.com/docs/pricing -->
<!-- Keep only the pricing table portion -->
<table>
<tr><th>Model</th><th>Input</th><th>Output</th></tr>
<tr><td>GPT-4o</td><td>$2.50 / 1M tokens</td><td>$10.00 / 1M tokens</td></tr>
<tr><td>GPT-4o-mini</td><td>$0.15 / 1M tokens</td><td>$0.60 / 1M tokens</td></tr>
</table>
```

- [ ] **Step 3: Run test to verify fixtures load**

```python
# collector/tests/test_fetcher.py
from tests.conftest import load_fixture, load_fixture_json

def test_load_fixtures():
    html = load_fixture("openai_models_page.html")
    assert "gpt-4o" in html
    data = load_fixture_json("openrouter_models.json")
    assert len(data["data"]) == 3
```

Run: `cd collector && python -m pytest tests/test_fetcher.py -v`
Expected: PASS (if fixtures exist) or FAIL (need to create them)

- [ ] **Step 4: Commit**

```bash
cd collector && git add -A && git commit -m "test: add test fixtures from real sources"
```

### Task 3: TursoDB client

**Files:**
- Create: `collector/src/modelinfo/db.py`
- Create: `collector/tests/test_db.py`

- [ ] **Step 1: Write failing test**

Create `collector/tests/test_db.py` with tests for: init_schema creates 3 tables, upsert_model inserts and is idempotent, get_latest_pricing returns most recent by valid_from.

```python
import pytest
from modelinfo.db import Database, init_schema

def test_init_schema_creates_tables():
    db = Database(url="file:test.db", auth_token="")
    init_schema(db)
    tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [r[0] for r in tables]
    for t in ["models", "pricing", "evaluations"]:
        assert t in table_names

def test_upsert_model_idempotent():
    db = Database(url="file:test.db", auth_token="")
    init_schema(db)
    data = {"model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"}
    db.upsert_model(data)
    db.upsert_model(data)  # no error
    rows = db.execute("SELECT count(*) FROM models WHERE model_id=?", ["openai/gpt-4o"])
    assert rows[0][0] == 1

def test_get_latest_pricing():
    db = Database(url="file:test.db", auth_token="")
    init_schema(db)
    db.upsert_pricing({"pricing_id": "a/o/global/2025-01-01", "model_id": "a", "channel": "official", "valid_from": "2025-01-01", "input_price_per_1m": 2.5, "output_price_per_1m": 10.0})
    db.upsert_pricing({"pricing_id": "a/o/global/2025-03-01", "model_id": "a", "channel": "official", "valid_from": "2025-03-01", "input_price_per_1m": 2.0, "output_price_per_1m": 8.0})
    latest = db.get_latest_pricing("a", "official", "global")
    assert latest["input_price_per_1m"] == 2.0
```

- [ ] **Step 2: Run test — expected FAIL**

`cd collector && python -m pytest tests/test_db.py -v` — ModuleNotFoundError

- [ ] **Step 3: Implement Database class**

`collector/src/modelinfo/db.py`: Database class wrapping libsql_client.create_client. Methods: execute(sql, params), upsert_model/pricing/evaluation (INSERT OR REPLACE with ON CONFLICT DO UPDATE), get_all_models, get_latest_pricing, get_all_pricing_for_model. Also includes SCHEMA_SQL string with CREATE TABLE IF NOT EXISTS for models, pricing, evaluations, change_log tables matching the spec schema. init_schema(db) function executes the DDL statements.

- [ ] **Step 4: Run tests** — `cd collector && python -m pytest tests/test_db.py -v` — 3 PASS

- [ ] **Step 5: Commit** — `feat: TursoDB client with schema init and upsert operations`


### Task 4: HTTP Fetcher with retry

**Files:**
- Create: `collector/src/modelinfo/fetcher.py`
- Modify: `collector/tests/test_fetcher.py`

- [ ] **Step 1: Write failing test**

In `collector/tests/test_fetcher.py`, test Fetcher async context manager:
- `test_fetch_json_success(httpx_mock)`: mock a JSON endpoint, verify returned dict
- `test_fetch_html_success(httpx_mock)`: mock an HTML page, verify BeautifulSoup object with parsed body
- `test_fetch_retry_on_500(httpx_mock)`: mock 2x 500 then 200, verify 3 requests made
- `test_fetch_exhausts_retries(httpx_mock)`: mock 3x 500, verify httpx.HTTPStatusError raised

- [ ] **Step 2: Run test — expected FAIL**

`cd collector && python -m pytest tests/test_fetcher.py -v` — ModuleNotFoundError

- [ ] **Step 3: Implement Fetcher**

```python
# collector/src/modelinfo/fetcher.py
import asyncio
import httpx
import structlog
from bs4 import BeautifulSoup

logger = structlog.get_logger()


class Fetcher:
    def __init__(self, max_retries: int = 3, timeout: float = 30.0):
        self.max_retries = max_retries
        self._client = httpx.AsyncClient(timeout=timeout, headers={
            "User-Agent": "ModelInfo-Collector/0.1 (automated metadata collection)"
        })

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self._client.aclose()

    async def fetch_json(self, url: str) -> dict:
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning("fetch_json_failed", url=url, attempt=attempt, error=str(e))
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)

    async def fetch_html(self, url: str) -> BeautifulSoup:
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = await self._client.get(url)
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "lxml")
            except Exception as e:
                logger.warning("fetch_html_failed", url=url, attempt=attempt, error=str(e))
                if attempt == self.max_retries:
                    raise
                await asyncio.sleep(2 ** attempt)
```

- [ ] **Step 4: Run tests** — `cd collector && python -m pytest tests/test_fetcher.py -v` — 4 PASS

- [ ] **Step 5: Commit** — `feat: async HTTP fetcher with exponential backoff retry`

### Task 5: Base parser interface + OpenRouter parser

**Files:**
- Create: `collector/src/modelinfo/parsers/__init__.py`
- Create: `collector/src/modelinfo/parsers/base.py`
- Create: `collector/src/modelinfo/parsers/openrouter.py`
- Create: `collector/tests/parsers/__init__.py`
- Create: `collector/tests/parsers/test_openrouter.py`

- [ ] **Step 1: Define base parser**

```python
# collector/src/modelinfo/parsers/base.py
from abc import ABC, abstractmethod
from modelinfo.fetcher import Fetcher


class BaseParser(ABC):
    source_name: str = ""

    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher

    @abstractmethod
    async def fetch_models(self) -> list[dict]:
        ...

    @abstractmethod
    async def fetch_pricing(self) -> list[dict]:
        ...
```

- [ ] **Step 2: Write OpenRouter test**

In `collector/tests/parsers/test_openrouter.py`, use the openrouter_response fixture:
- `test_parse_models_structure`: verify each model dict has model_id, model_name, provider, capabilities, context_length
- `test_parse_pricing_structure`: verify pricing dicts have model_id, channel="marketplace", input_price_per_1m normalized from string "0.0000025" to float 2.5
- `test_capabilities_from_modality`: "text+image->text" maps to text=True, vision=True, code=False

- [ ] **Step 3: Run test — expected FAIL** — `cd collector && python -m pytest tests/parsers/test_openrouter.py -v`

- [ ] **Step 4: Implement OpenRouterParser**

```python
# collector/src/modelinfo/parsers/openrouter.py
from modelinfo.parsers.base import BaseParser

OPENROUTER_API = "https://openrouter.ai/api/v1/models"


class OpenRouterParser(BaseParser):
    source_name = "openrouter"

    def _url(self, model_id: str) -> str:
        return f"https://openrouter.ai/models/{model_id.split('/')[-1]}"

    async def fetch_models(self) -> list[dict]:
        data = await self.fetcher.fetch_json(OPENROUTER_API)
        models = []
        for m in data.get("data", []):
            caps = self._parse_capabilities(m)
            models.append({
                "model_id": m["id"],
                "model_name": m.get("name", m["id"]),
                "provider": m["id"].split("/")[0],
                "provider_type": "closed",
                "context_length": m.get("context_length"),
                "max_output_tokens": (m.get("top_provider") or {}).get("max_completion_tokens"),
                "capabilities": caps,
                "urls": '{"official": "' + self._url(m['id']) + '"}',
                "tags": self._derive_tags(caps),
            })
        return models

    async def fetch_pricing(self) -> list[dict]:
        data = await self.fetcher.fetch_json(OPENROUTER_API)
        pricings = []
        for m in data.get("data", []):
            p = m.get("pricing", {})
            if not p:
                continue
            pricings.append({
                "pricing_id": f"{m['id']}/openrouter/global/{self._today()}",
                "model_id": m["id"],
                "channel": "marketplace",
                "market_name": "openrouter",
                "region": "global",
                "valid_from": self._today(),
                "currency": "USD",
                "input_price_per_1m": float(p.get("prompt", 0)) * 1_000_000 if p.get("prompt") else None,
                "output_price_per_1m": float(p.get("completion", 0)) * 1_000_000 if p.get("completion") else None,
                "price_per_image": float(p.get("image")) if p.get("image") else None,
                "source": f"https://openrouter.ai/api/v1/models/{m['id']}",
            })
        return pricings

    def _parse_capabilities(self, m: dict) -> str:
        modality = m.get("architecture", {}).get("modality", "")
        caps = {
            "text": "text" in modality,
            "code": True,
            "vision": "image" in modality,
            "audio": "audio" in modality,
        }
        import json
        return json.dumps(caps)

    def _derive_tags(self, caps: dict) -> str:
        import json
        tags = []
        if caps.get("vision"):
            tags.append("multimodal")
        if caps.get("code"):
            tags.append("coding")
        return json.dumps(tags)

    @staticmethod
    def _today() -> str:
        from datetime import date
        return date.today().isoformat()
```

- [ ] **Step 5: Run tests** — `cd collector && python -m pytest tests/parsers/test_openrouter.py -v` — PASS

- [ ] **Step 6: Commit** — `feat: OpenRouter parser for models and pricing`


### Task 6: OpenAI parser

**Files:**
- Create: `collector/src/modelinfo/parsers/openai.py`
- Create: `collector/tests/parsers/test_openai.py`

- [ ] **Step 1: Write test using fixtures**

In `collector/tests/parsers/test_openai.py`:
- `test_parse_models_from_html(openai_models_html)`: parse HTML table, extract 2 models with model_id, model_name, context_length, max_output_tokens. Verify gpt-4o has context_length=128000.
- `test_parse_pricing_from_html(openai_pricing_html)`: parse pricing table, extract input/output prices. Verify GPT-4o input=2.50, output=10.00 per 1M.
- `test_parse_pricing_handles_cached`: when HTML contains cached pricing row, extract cache_read_price_per_1m.

- [ ] **Step 2: Run test - expected FAIL**

- [ ] **Step 3: Implement OpenAIParser**

`collector/src/modelinfo/parsers/openai.py`:
- Extends BaseParser, source_name="openai"
- `fetch_models()`: fetches https://platform.openai.com/docs/models, parses the models table with BeautifulSoup. Each tr yields a model dict. Handles Context window column parsing 128,000 to 128000. Accepts html_override for testing.
- `fetch_pricing()`: fetches https://platform.openai.com/docs/pricing, parses pricing table. Handles format `$2.50 / 1M tokens` using regex `\$(\d+\.?\d*)\s*/\s*1M`.

- [ ] **Step 4: Run tests** - PASS

- [ ] **Step 5: Commit** - `feat: OpenAI docs parser for models and pricing`

### Task 7: Anthropic parser

**Files:**
- Create: `collector/src/modelinfo/parsers/anthropic.py`
- Create: `collector/tests/parsers/test_anthropic.py`

- [ ] **Step 1: Write test using fixtures**

In `collector/tests/parsers/test_anthropic.py`:
- `test_parse_models_from_html(anthropic_models_html)`: extract Claude model names, context_length values
- `test_parse_pricing_from_html(anthropic_pricing_html)`: extract pricing, verify reasoning_tokens_charged is detected
- `test_capabilities_include_reasoning`: Anthropic models should have reasoning=True, vision=True

- [ ] **Step 2: Run test - expected FAIL**

- [ ] **Step 3: Implement AnthropicParser**

`collector/src/modelinfo/parsers/anthropic.py`:
- Extends BaseParser, source_name="anthropic"
- `fetch_models()`: fetches https://docs.anthropic.com/en/docs/about-claude/models
- `fetch_pricing()`: fetches https://www.anthropic.com/pricing. Special handling for reasoning_tokens_charged=True on Claude thinking models.
- Same html_override pattern for testing.

- [ ] **Step 4: Run tests** - PASS

- [ ] **Step 5: Commit** - `feat: Anthropic docs parser with reasoning token detection`

### Task 8: Normalizer

**Files:**
- Create: `collector/src/modelinfo/normalizer.py`
- Create: `collector/tests/test_normalizer.py`

- [ ] **Step 1: Write test**

```python
# collector/tests/test_normalizer.py
from modelinfo.normalizer import (
    normalize_model_id, normalize_price_to_1m, normalize_context_length,
    normalize_date, normalize_tags,
)

def test_normalize_model_id():
    assert normalize_model_id("openai/gpt-4o") == "openai/gpt-4o"
    assert normalize_model_id("GPT-4o", provider="openai") == "openai/gpt-4o"

def test_normalize_price_to_1m():
    assert normalize_price_to_1m("0.0000025") == 2.5
    assert normalize_price_to_1m(2.5) == 2.5
    assert normalize_price_to_1m(None) is None
    assert normalize_price_to_1m("$2.50 / 1M tokens") == 2.5

def test_normalize_context_length():
    assert normalize_context_length("128,000") == 128000
    assert normalize_context_length("128K") == 128000
    assert normalize_context_length("1M") == 1000000
    assert normalize_context_length(128000) == 128000
    assert normalize_context_length(None) is None

def test_normalize_tags():
    assert "chat" in normalize_tags(["chat", "vision", "  CODING  "])
    assert normalize_tags([]) == []
```

- [ ] **Step 2: Run test - expected FAIL**

- [ ] **Step 3: Implement**

`collector/src/modelinfo/normalizer.py`:
- `normalize_model_id(raw, provider)`: lowercase, "provider/name" format
- `normalize_price_to_1m(raw)`: regex extract number, convert per-token to per-1M (*1_000_000), handle None
- `normalize_context_length(raw)`: parse "128K"->128000, "1M"->1000000, strip commas, pass-through int
- `normalize_date(raw)`: parse various formats to "YYYY-MM-DD"
- `normalize_tags(raw_list)`: lowercase, strip, deduplicate, sort

- [ ] **Step 4: Run tests** - PASS

- [ ] **Step 5: Commit** - `feat: field normalizer for prices, context lengths, dates, and tags`

### Task 9: Differ

**Files:**
- Create: `collector/src/modelinfo/differ.py`
- Create: `collector/tests/test_differ.py`

- [ ] **Step 1: Write test**

```python
# collector/tests/test_differ.py
from modelinfo.differ import diff_models, diff_pricing

def test_diff_models_detects_new():
    old = {}
    new = {"openai/gpt-4o": {"model_name": "GPT-4o", "context_length": 128000}}
    added, updated, unchanged = diff_models(old, new)
    assert len(added) == 1
    assert added[0].model_id == "openai/gpt-4o"

def test_diff_models_detects_change():
    old = {"openai/gpt-4o": {"context_length": 128000}}
    new = {"openai/gpt-4o": {"context_length": 256000}}
    added, updated, unchanged = diff_models(old, new)
    assert len(updated) == 1
    assert updated[0].field_name == "context_length"

def test_diff_models_detects_unchanged():
    old = {"openai/gpt-4o": {"context_length": 128000}}
    new = {"openai/gpt-4o": {"context_length": 128000}}
    added, updated, unchanged = diff_models(old, new)
    assert len(unchanged) == 1

def test_diff_pricing_detects_price_change():
    old = [{"pricing_id": "a", "input_price_per_1m": 2.5, "output_price_per_1m": 10.0}]
    new = [{"pricing_id": "b", "input_price_per_1m": 2.0, "output_price_per_1m": 8.0}]
    changed, unchanged = diff_pricing("x", old, new)
    assert any(c.field_name == "input_price_per_1m" for c in changed)
```

- [ ] **Step 2: Run test - expected FAIL**

- [ ] **Step 3: Implement**

`collector/src/modelinfo/differ.py`:
- `diff_models(old: dict, new: dict)` -> `(added, updated, unchanged)` where added/updated are lists of ChangeRecord
- `diff_pricing(model_id, old_pricing, new_pricing)` -> `(changed, unchanged)`
- Compares field by field, converts values to strings for comparison
- Price fields tracked separately: input_price_per_1m, output_price_per_1m, cache_read/write, price_per_request, price_per_image, free_tier_tokens

- [ ] **Step 4: Run tests** - PASS

- [ ] **Step 5: Commit** - `feat: differ for detecting model and pricing changes`

### Task 10: Writer + Validator

**Files:**
- Create: `collector/src/modelinfo/writer.py`
- Create: `collector/src/modelinfo/validator.py`
- Create: `collector/tests/test_writer.py`
- Create: `collector/tests/test_validator.py`

- [ ] **Step 1: Write validator tests**

```python
# collector/tests/test_validator.py
from modelinfo.validator import validate_model, validate_pricing

def test_validate_model_missing_required():
    errors = validate_model({"model_name": "Test"})  # missing model_id, provider
    assert len(errors) > 0

def test_validate_model_valid():
    errors = validate_model({"model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"})
    assert len(errors) == 0

def test_validate_pricing_negative_price():
    errors = validate_pricing({"pricing_id": "x", "model_id": "x", "valid_from": "2025-01-01", "input_price_per_1m": -1.0})
    assert any("negative" in e.lower() for e in errors)

def test_validate_pricing_unreasonable_price():
    errors = validate_pricing({"pricing_id": "x", "model_id": "x", "valid_from": "2025-01-01", "input_price_per_1m": 1000.0})
    assert any("unreasonable" in e.lower() for e in errors)
```

- [ ] **Step 2: Write writer tests**

```python
# collector/tests/test_writer.py
from modelinfo.writer import Writer
from modelinfo.db import Database, init_schema

def test_writer_upserts_models():
    db = Database(url="file:test.db", auth_token="")
    init_schema(db)
    writer = Writer(db)
    models = [{"model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"}]
    result = writer.write_models(models)
    assert result["upserted"] == 1
    rows = db.execute("SELECT model_name FROM models WHERE model_id='openai/gpt-4o'")
    assert rows[0][0] == "GPT-4o"

def test_writer_records_changes():
    db = Database(url="file:test.db", auth_token="")
    init_schema(db)
    writer = Writer(db)
    changes = writer.write_models([{"model_id": "openai/gpt-4o", "model_name": "GPT-4o", "provider": "openai"}])
    assert changes["changes_written"] >= 0
```

- [ ] **Step 3: Run tests - expected FAIL**

- [ ] **Step 4: Implement Writer**

`collector/src/modelinfo/writer.py`:
- `Writer(db: Database)` class
- `write_models(models: list[dict])` -> dict with counts: upserted, errors, changes_written
- `write_pricing(pricings: list[dict])` -> dict
- `write_evaluations(evals: list[dict])` -> dict
- Internally calls db.upsert_model/pricing/evaluation and records ChangeRecords

- [ ] **Step 5: Implement Validator**

`collector/src/modelinfo/validator.py`:
- `validate_model(data: dict)` -> list[str]: checks model_id, model_name, provider are present; context_length > 0; max_output_tokens > 0
- `validate_pricing(data: dict)` -> list[str]: checks prices are non-negative; flags unreasonable prices (input > $100/1M, output > $500/1M)
- `validate_evaluation(data: dict)` -> list[str]: checks scores in 0-100 range; benchmark scores reasonable

- [ ] **Step 6: Run tests** - PASS

- [ ] **Step 7: Commit** - `feat: writer and validator with sanity checks`


### Task 11: Change log and Error tracking

**Files:**
- Create: `collector/src/modelinfo/change_log.py`
- Create: `collector/tests/test_change_log.py`

ChangeLogManager writes change records to `logs/change_log.md` with date headers and markdown table rows. ErrorTracker writes parse errors to `logs/errors.jsonl`. `should_create_issue(source)` returns True after 3 consecutive failures for a source.

Tests verify: change_log.md is created and contains expected content, error counter triggers after 3x failures, errors are JSONL formatted.

### Task 12: CLI with Typer

**Files:**
- Create: `collector/src/modelinfo/cli.py`
- Create: `collector/tests/test_cli.py`

Commands:
- `collect models|pricing|evaluations|all [--source openrouter|openai|anthropic|all] [--dry-run]`
- `diff [--dry-run]`
- `--help`

The CLI initializes DB, runs selected parsers, validates output, writes via Writer. On parse failure, logs to ErrorTracker and warns if should_create_issue. Uses asyncio.run() internally.

### Task 13: GitHub Actions workflows

**Files:**
- Create: `.github/workflows/daily-price-check.yml`
- Create: `.github/workflows/weekly-full-collect.yml`

Daily: cron `0 8 * * *`, runs `collect pricing`, commits change_log.md.
Weekly: cron `0 2 * * 1`, runs `collect all`, commits change_log.md + errors.jsonl.
Both support workflow_dispatch for manual trigger.
Secrets: TURSO_DB_URL, TURSO_AUTH_TOKEN via GitHub Secrets.

### Task 14: Integration test

**Files:**
- Create: `collector/tests/test_integration.py`

End-to-end test with httpx_mock: registers mock responses for OpenRouter + OpenAI, runs full pipeline (fetch -> parse -> validate -> write), verifies DB has expected rows. Also tests idempotency: running the same fetch twice produces fewer or zero changes on second run.

### Task 15: README and final wiring

**Files:**
- Create: `collector/README.md`

Covers: project overview, quick start, env var setup, CLI commands reference, and how to add a new parser source (4-step guide).

Final verification: `cd collector && python -m pytest tests/ -v` — all tests pass.
