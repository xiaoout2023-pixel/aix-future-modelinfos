import json
import structlog
from datetime import datetime, timezone

logger = structlog.get_logger()

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
    last_verified TEXT
);

CREATE TABLE IF NOT EXISTS evaluations (
    eval_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,
    eval_date TEXT NOT NULL,
    source TEXT NOT NULL,
    mmlu REAL,
    mmlu_pro REAL,
    gpqa REAL,
    aa_intelligence_index REAL,
    aa_coding_index REAL,
    aa_math_index REAL,
    hle REAL,
    aime REAL,
    livecodebench REAL,
    scicode REAL,
    ifbench REAL,
    aa_lcr REAL,
    lmarena_elo REAL,
    lmarena_coding REAL,
    lmarena_math REAL,
    lmarena_hard REAL,
    other_benchmarks TEXT,
    tokens_per_second INTEGER,
    avg_latency_ms INTEGER,
    p95_latency_ms INTEGER,
    ttft_ms INTEGER,
    reasoning_level TEXT,
    overall_score REAL,
    cost_efficiency_score REAL
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

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_pricing_model_id ON pricing(model_id);
CREATE INDEX IF NOT EXISTS idx_pricing_lookup ON pricing(model_id, channel, region, valid_from);
CREATE INDEX IF NOT EXISTS idx_evaluations_model_id ON evaluations(model_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_source ON evaluations(source);
CREATE INDEX IF NOT EXISTS idx_change_log_model_id ON change_log(model_id);
CREATE INDEX IF NOT EXISTS idx_change_log_table ON change_log(table_name, changed_at);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(columns: list[str], row: list) -> dict:
    return dict(zip(columns, row))


class Database:
    """Thin wrapper around libsql-client for TursoDB (or local SQLite)."""

    def __init__(self, url: str, auth_token: str):
        import libsql_client

        if url.startswith("libsql://"):
            url = url.replace("libsql://", "https://")

        if url.startswith("file:"):
            self._client = libsql_client.create_client_sync(url)
        elif url.startswith("http://") or url.startswith("https://"):
            self._client = libsql_client.create_client_sync(url, auth_token=auth_token)
        else:
            raise ValueError(f"Unsupported database URL scheme: {url}")

        self._column_cache: dict[str, list[str]] = {}

    def close(self):
        try:
            self._client.close()
        except Exception:
            pass

    def execute(self, sql: str, params=None) -> list[list]:
        try:
            result = self._client.execute(sql, params or [])
            return [list(row) for row in result.rows]
        except KeyError as e:
            logger.error("db_key_error", sql=sql[:200], params=str(params)[:200] if params else None, error=str(e))
            raise RuntimeError(f"Database returned unexpected response for SQL [{sql[:100]}]: missing key {e}") from e
        except Exception as e:
            err_msg = str(e)
            logger.error("db_execute_failed", sql=sql[:200], error=err_msg)
            raise

    def _get_columns(self, table: str) -> list[str]:
        if table in self._column_cache:
            return self._column_cache[table]
        rows = self.execute(f"PRAGMA table_info({table})")
        cols = [r[1] for r in rows]
        self._column_cache[table] = cols
        return cols

    def batch_upsert(self, table: str, rows: list[dict], pk: str, batch_size: int = 50):
        """Batch upsert multiple rows in a single SQL statement.

        Falls back to per-row upsert on error to isolate problematic records.
        """
        if not rows:
            return
        columns = self._get_columns(table)
        # Normalize all rows to the same column set (fill missing with None)
        filtered_rows = []
        for r in rows:
            f = {c: r.get(c) for c in columns if c in r}
            if f:
                filtered_rows.append(f)
        if not filtered_rows:
            return

        # Use the intersection of columns to ensure all rows have values
        common_cols = list(filtered_rows[0].keys())
        for r in filtered_rows:
            for c in common_cols:
                r.setdefault(c, None)

        col_list = ", ".join(common_cols)
        single_placeholders = "(" + ", ".join(["?"] * len(common_cols)) + ")"
        set_clause = ", ".join(f"{c} = excluded.{c}" for c in common_cols if c != pk)

        for i in range(0, len(filtered_rows), batch_size):
            batch = filtered_rows[i:i + batch_size]
            batch_placeholders = ", ".join([single_placeholders] * len(batch))
            if set_clause:
                sql = (
                    f"INSERT INTO {table} ({col_list}) VALUES {batch_placeholders} "
                    f"ON CONFLICT({pk}) DO UPDATE SET {set_clause}"
                )
            else:
                sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES {batch_placeholders}"
            params = [r[c] for r in batch for c in common_cols]
            try:
                self.execute(sql, params)
            except Exception as e:
                logger.warning("db_batch_upsert_failed", table=table, batch_size=len(batch), error=str(e))
                # Fallback to per-row upsert for this batch
                for r in batch:
                    try:
                        self._do_upsert(table, r, pk)
                    except Exception as e2:
                        logger.warning("db_batch_fallback_failed", table=table, pk=r.get(pk), error=str(e2))

    def _do_upsert(self, table: str, data: dict, pk: str):
        columns = self._get_columns(table)
        filtered = {k: data[k] for k in data if k in columns}
        col_names = list(filtered.keys())
        if not col_names:
            logger.warning("db_upsert_no_columns", table=table, pk=data.get(pk))
            return
        placeholders = ", ".join(["?"] * len(col_names))
        col_list = ", ".join(col_names)
        set_clause = ", ".join(f"{c} = excluded.{c}" for c in col_names if c != pk)
        if not set_clause:
            sql = f"INSERT OR IGNORE INTO {table} ({col_list}) VALUES ({placeholders})"
        else:
            sql = (
                f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
                f"ON CONFLICT({pk}) DO UPDATE SET {set_clause}"
            )
        values = [filtered[c] for c in col_names]
        self.execute(sql, values)

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

    def upsert_models(self, rows: list[dict]):
        for r in rows:
            r.setdefault("status", "active")
            r.setdefault("aliases", "[]")
            r.setdefault("capabilities", "{}")
            r.setdefault("regions", "[]")
            r.setdefault("private_deployment", 0)
            r.setdefault("openai_compatible", 0)
            r.setdefault("urls", "{}")
            r.setdefault("tags", "[]")
            r["last_updated"] = r.get("last_updated") or _now_iso()
        self.batch_upsert("models", rows, "model_id")

    def upsert_pricing(self, data: dict):
        data.setdefault("channel", "official")
        data.setdefault("region", "global")
        data.setdefault("currency", "USD")
        data.setdefault("reasoning_tokens_charged", 0)
        data.setdefault("has_spot", 0)
        data["last_verified"] = data.get("last_verified") or _now_iso()
        self._do_upsert("pricing", data, "pricing_id")

    def upsert_pricings(self, rows: list[dict]):
        for r in rows:
            r.setdefault("channel", "official")
            r.setdefault("region", "global")
            r.setdefault("currency", "USD")
            r.setdefault("reasoning_tokens_charged", 0)
            r.setdefault("has_spot", 0)
            r["last_verified"] = r.get("last_verified") or _now_iso()
        self.batch_upsert("pricing", rows, "pricing_id")

    def upsert_evaluation(self, data: dict):
        self._do_upsert("evaluations", data, "eval_id")

    def upsert_evaluations(self, rows: list[dict]):
        self.batch_upsert("evaluations", rows, "eval_id")

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
    """Execute all CREATE TABLE IF NOT EXISTS statements and run migrations."""
    for statement in SCHEMA_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                db.execute(stmt)
            except Exception as e:
                logger.warning("init_schema_create_failed", sql=stmt[:80], error=str(e))

    # Create indexes for query performance (idempotent)
    for statement in INDEX_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            try:
                db.execute(stmt)
            except Exception as e:
                logger.warning("init_schema_index_failed", sql=stmt[:80], error=str(e))

    try:
        db.execute("PRAGMA foreign_keys = OFF")
    except Exception:
        pass

    _migrate_evaluations_table(db)
    _rebuild_evaluations_if_stale(db)


EVALUATIONS_NEW_COLUMNS = [
    "aa_intelligence_index", "aa_coding_index", "aa_math_index",
    "hle", "aime", "livecodebench", "scicode", "ifbench", "aa_lcr",
    "lmarena_coding", "lmarena_math", "lmarena_hard",
]


def _migrate_evaluations_table(db: Database):
    try:
        existing = db._get_columns("evaluations")
    except Exception as e:
        logger.warning("migrate_get_columns_failed", error=str(e))
        return
    for col in EVALUATIONS_NEW_COLUMNS:
        if col not in existing:
            try:
                db.execute(f"ALTER TABLE evaluations ADD COLUMN {col} REAL")
                logger.info("db_migration", action="add_column", table="evaluations", column=col)
            except Exception as e:
                logger.warning("migrate_add_column_failed", column=col, error=str(e))


def _rebuild_evaluations_if_stale(db: Database):
    try:
        existing = db._get_columns("evaluations")
    except Exception as e:
        logger.warning("rebuild_get_columns_failed", error=str(e))
        return

    stale_cols = {"gsm8k", "math_500", "arc_challenge", "humaneval", "swe_bench", "needle_haystack", "bfcl"}
    if not (stale_cols & set(existing)):
        return

    logger.info("db_migration", action="rebuild_evaluations", reason="stale_schema_detected")
    try:
        db.execute("DROP TABLE evaluations")
    except Exception as e:
        logger.warning("rebuild_drop_failed", error=str(e))
        return

    for statement in SCHEMA_SQL.strip().split(";"):
        stmt = statement.strip()
        if stmt and "evaluations" in stmt:
            try:
                db.execute(stmt)
            except Exception as e:
                logger.error("rebuild_create_failed", error=str(e))
