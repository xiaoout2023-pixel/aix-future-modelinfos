import json
from datetime import datetime, timezone

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    provider TEXT NOT NULL,
    provider_type TEXT,
    release_date TEXT,
    status TEXT DEFAULT 'active',
    aliases TEXT DEFAULT '[]',
    capabilities TEXT DEFAULT '{}',
    context_length INTEGER,
    max_output_tokens INTEGER,
    regions TEXT DEFAULT '[]',
    private_deployment INTEGER DEFAULT 0,
    openai_compatible INTEGER DEFAULT 0,
    urls TEXT DEFAULT '{}',
    tags TEXT DEFAULT '[]',
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS pricing (
    pricing_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    channel TEXT DEFAULT 'official',
    market_name TEXT,
    region TEXT DEFAULT 'global',
    valid_from TEXT NOT NULL,
    currency TEXT DEFAULT 'USD',
    input_price_per_1m REAL,
    output_price_per_1m REAL,
    cache_read_price_per_1m REAL,
    cache_write_price_per_1m REAL,
    reasoning_tokens_charged INTEGER DEFAULT 0,
    reasoning_overhead_ratio REAL,
    price_per_request REAL,
    price_per_image REAL,
    price_per_audio_min REAL,
    tiers TEXT,
    volume_discount TEXT,
    reserved_discount_pct REAL,
    free_tier_tokens INTEGER,
    min_billable_tokens INTEGER,
    rounding_unit INTEGER,
    has_spot INTEGER DEFAULT 0,
    source TEXT,
    last_verified TEXT,
    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE TABLE IF NOT EXISTS evaluations (
    eval_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    eval_date TEXT NOT NULL,
    source TEXT NOT NULL,
    mmlu REAL,
    gsm8k REAL,
    humaneval REAL,
    other_benchmarks TEXT,
    tokens_per_second INTEGER,
    avg_latency_ms INTEGER,
    p95_latency_ms INTEGER,
    reasoning_level TEXT,
    overall_score REAL,
    cost_efficiency_score REAL,
    FOREIGN KEY (model_id) REFERENCES models(model_id)
);

CREATE TABLE IF NOT EXISTS change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT NOT NULL,
    model_id TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_at TEXT NOT NULL,
    source_url TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(columns: list[str], row: list) -> dict:
    return dict(zip(columns, row))


class Database:
    """Thin wrapper around libsql-client for TursoDB (or local SQLite)."""

    def __init__(self, url: str, auth_token: str):
        import libsql_client

        # libsql:// uses WebSocket which can be unreliable; convert to https://
        if url.startswith("libsql://"):
            url = url.replace("libsql://", "https://")

        if url.startswith("file:"):
            self._client = libsql_client.create_client_sync(url)
        elif url.startswith("http://") or url.startswith("https://"):
            self._client = libsql_client.create_client_sync(url, auth_token=auth_token)
        else:
            raise ValueError(f"Unsupported database URL scheme: {url}")

    def execute(self, sql: str, params=None) -> list[list]:
        result = self._client.execute(sql, params or [])
        return [list(row) for row in result.rows]

    # -- helpers --------------------------------------------------------------

    def _get_columns(self, table: str) -> list[str]:
        rows = self.execute(f"PRAGMA table_info({table})")
        return [r[1] for r in rows]

    def _do_upsert(self, table: str, data: dict, pk: str):
        columns = self._get_columns(table)
        filtered = {k: data[k] for k in data if k in columns}
        col_names = list(filtered.keys())
        placeholders = ", ".join(["?"] * len(col_names))
        col_list = ", ".join(col_names)
        set_clause = ", ".join(f"{c} = excluded.{c}" for c in col_names if c != pk)
        sql = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT({pk}) DO UPDATE SET {set_clause}"
        )
        values = [filtered[c] for c in col_names]
        self.execute(sql, values)

    # -- public API -----------------------------------------------------------

    def upsert_model(self, data: dict):
        data.setdefault("status", "active")
        data.setdefault("aliases", "[]")
        data.setdefault("capabilities", "{}")
        data.setdefault("regions", "[]")
        data.setdefault("private_deployment", 0)
        data.setdefault("openai_compatible", 0)
        data.setdefault("urls", "{}")
        data.setdefault("tags", "[]")
        data["last_updated"] = data.get("last_updated") or _now_iso()
        self._do_upsert("models", data, "model_id")

    def upsert_pricing(self, data: dict):
        data.setdefault("channel", "official")
        data.setdefault("region", "global")
        data.setdefault("currency", "USD")
        data.setdefault("reasoning_tokens_charged", 0)
        data.setdefault("has_spot", 0)
        data["last_verified"] = data.get("last_verified") or _now_iso()
        self._do_upsert("pricing", data, "pricing_id")

    def upsert_evaluation(self, data: dict):
        self._do_upsert("evaluations", data, "eval_id")

    def get_all_models(self) -> list[dict]:
        columns = self._get_columns("models")
        rows = self.execute("SELECT * FROM models")
        return [_row_to_dict(columns, row) for row in rows]

    def get_latest_pricing(
        self, model_id: str, channel: str, region: str
    ) -> dict | None:
        sql = (
            "SELECT * FROM pricing WHERE model_id = ? AND channel = ? AND region = ? "
            "ORDER BY valid_from DESC LIMIT 1"
        )
        rows = self.execute(sql, [model_id, channel, region])
        if not rows:
            return None
        columns = self._get_columns("pricing")
        return _row_to_dict(columns, rows[0])

    def get_all_pricing_for_model(self, model_id: str) -> list[dict]:
        columns = self._get_columns("pricing")
        rows = self.execute("SELECT * FROM pricing WHERE model_id = ?", [model_id])
        return [_row_to_dict(columns, row) for row in rows]


def init_schema(db: Database):
    """Execute all CREATE TABLE IF NOT EXISTS statements."""
    for statement in SCHEMA_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            db.execute(stmt)
