"""Snapshot manager: stores DB state as JSON files for diff without DB reads.

The snapshot files are committed to git alongside change_log.md, so each workflow
run can load the previous state from file (fast, free) instead of querying the
database (slow, costs TursoDB rows-read quota).
"""
import json
from pathlib import Path
import structlog

logger = structlog.get_logger()

# Default: collector/snapshots/ (committed to git)
SNAPSHOT_DIR = Path(__file__).resolve().parent.parent.parent / "snapshots"


class SnapshotManager:
    """Load/save JSON snapshots keyed by primary key."""

    def __init__(self, base_dir: Path | None = None):
        self.base_dir = Path(base_dir) if base_dir else SNAPSHOT_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        # In-memory cache for the current process
        self._cache: dict[str, dict] = {}
        self._dirty: set[str] = set()

    def _path(self, name: str) -> Path:
        return self.base_dir / f"{name}.json"

    def load(self, name: str) -> dict:
        """Load snapshot as a dict keyed by PK. Returns empty dict if missing."""
        if name in self._cache:
            return self._cache[name]
        path = self._path(name)
        if not path.exists():
            self._cache[name] = {}
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                logger.warning("snapshot_invalid_format", name=name)
                data = {}
            self._cache[name] = data
            return data
        except Exception as e:
            logger.warning("snapshot_load_failed", name=name, error=str(e))
            self._cache[name] = {}
            return {}

    def save(self, name: str, data: dict):
        """Save full snapshot dict to file."""
        path = self._path(name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self._cache[name] = data
            self._dirty.discard(name)
        except Exception as e:
            logger.warning("snapshot_save_failed", name=name, error=str(e))

    def update(self, name: str, new_rows: list[dict], pk: str):
        """Merge new rows into existing snapshot and persist to disk.

        Called after a successful DB write so the snapshot stays in sync.
        """
        snapshot = dict(self.load(name))  # shallow copy
        for row in new_rows:
            key = row.get(pk)
            if key is not None and key != "":
                # Only store JSON-serializable values
                snapshot[str(key)] = _make_json_safe(row)
        self.save(name, snapshot)

    def get_pricing_for_model(self, model_id: str) -> list[dict]:
        """Helper: return pricing rows for a model, sorted by valid_from DESC.

        Mirrors the previous DB query `get_all_pricing_for_model` but reads
        from the in-memory snapshot instead.
        """
        snapshot = self.load("pricing")
        rows = [v for v in snapshot.values() if v.get("model_id") == model_id]
        # Sort by valid_from DESC (latest first), matching DB ORDER BY behavior
        rows.sort(key=lambda x: x.get("valid_from") or "", reverse=True)
        return rows


def _make_json_safe(value):
    """Recursively convert value to JSON-safe types."""
    if isinstance(value, dict):
        return {str(k): _make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_make_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    # Convert anything else (datetime, etc.) to string
    return str(value)
