import json
from datetime import datetime, timezone
from pathlib import Path


class ChangeLogManager:
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def write(self, changes: list, source_name: str = ""):
        if not changes:
            return
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        log_path = self.log_dir / "change_log.md"
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"\n## {today} - {source_name}\n\n")
            for c in changes:
                f.write(f"- **{c.table_name}.{c.field_name}** | {c.model_id} | "
                        f"`{c.old_value}` -> `{c.new_value}`")
                if c.source_url:
                    f.write(f" | [source]({c.source_url})")
                f.write("\n")


class ErrorTracker:
    def __init__(self, error_dir: str = "logs"):
        self.error_dir = Path(error_dir)
        self.error_dir.mkdir(parents=True, exist_ok=True)
        self.errors_file = self.error_dir / "errors.jsonl"

    def log_error(self, source: str, url: str, error: str):
        entry = {
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "source": source,
            "url": url,
            "error": error,
        }
        with open(self.errors_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_recent_errors(self, source: str | None = None, days: int = 7) -> list[dict]:
        if not self.errors_file.exists():
            return []
        cutoff = datetime.now(tz=timezone.utc).timestamp() - days * 86400
        results = []
        with open(self.errors_file, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                entry = json.loads(line)
                ts = datetime.fromisoformat(entry["timestamp"]).timestamp()
                if ts >= cutoff and (source is None or entry["source"] == source):
                    results.append(entry)
        return results

    def should_create_issue(self, source: str) -> bool:
        recent = self.get_recent_errors(source=source)
        return len(recent) >= 3
