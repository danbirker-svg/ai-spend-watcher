"""Cache management utilities for AI Spend Watcher."""

import json
from pathlib import Path
from typing import Any

from .config import CACHE_DIR


def clear_cache() -> int:
    """Clear all cached data. Returns number of files removed."""
    count = 0
    if CACHE_DIR.exists():
        for f in CACHE_DIR.glob("*.json"):
            f.unlink()
            count += 1
    return count


def cache_stats() -> dict[str, Any]:
    """Get cache statistics."""
    if not CACHE_DIR.exists():
        return {
            "files": 0,
            "total_size_bytes": 0,
            "total_size_human": _human_size(0),
            "cache_dir": str(CACHE_DIR),
        }

    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)

    return {
        "files": len(files),
        "total_size_bytes": total_size,
        "total_size_human": _human_size(total_size),
        "cache_dir": str(CACHE_DIR),
    }


def _human_size(size: int) -> str:
    s = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if s < 1024:
            return f"{s:.1f} {unit}"
        s /= 1024
    return f"{s:.1f} TB"
