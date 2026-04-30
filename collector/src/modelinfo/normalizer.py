import re
from datetime import datetime


def normalize_model_id(raw: str, provider: str | None = None) -> str:
    """Normalize to 'provider/model-name' format, lowercase."""
    raw = raw.strip().lower()
    if "/" in raw:
        return raw
    if provider:
        return f"{provider.lower()}/{raw}"
    return raw


def normalize_price_to_1m(raw: str | float | int | None) -> float | None:
    """Convert any price format to USD per 1M tokens."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    raw = str(raw).strip()
    if not raw:
        return None
    # Extract number from formats like "$2.50 / 1M tokens" or "0.0000025"
    match = re.search(r'(\d+\.?\d*)', raw)
    if not match:
        return None
    value = float(match.group(1))
    # If value looks like per-token pricing (< 0.01), convert to per-1M
    if value < 0.01:
        value = value * 1_000_000
    return value


def normalize_context_length(raw: str | int | None) -> int | None:
    """Parse context length to int."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    raw = str(raw).strip().upper().replace(",", "")
    if not raw:
        return None
    if raw.endswith("K"):
        return int(float(raw[:-1]) * 1000)
    if raw.endswith("M"):
        return int(float(raw[:-1]) * 1_000_000)
    return int(raw)


def normalize_date(raw: str | None) -> str | None:
    """Normalize to YYYY-MM-DD format."""
    if raw is None:
        return None
    raw = str(raw).strip()
    # Already YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', raw):
        return raw
    # YYYY/MM/DD
    if re.match(r'^\d{4}/\d{2}/\d{2}$', raw):
        return raw.replace("/", "-")
    # Try common formats
    for fmt in ["%b %d, %Y", "%B %d, %Y", "%d %b %Y"]:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw


def normalize_tags(raw: list[str] | None) -> list[str]:
    """Deduplicate, lowercase, strip, sort."""
    if not raw:
        return []
    seen = set()
    result = []
    for tag in raw:
        t = tag.strip().lower()
        if t and t not in seen:
            seen.add(t)
            result.append(t)
    result.sort()
    return result
