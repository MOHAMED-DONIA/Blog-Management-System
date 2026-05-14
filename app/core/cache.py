"""
In-Memory TTL Cache
Simple thread-safe cache with time-to-live (TTL) expiry.
Designed for caching Posts and Comments — no Redis dependency required.
"""
import threading
import time
from typing import Any, Dict, Optional, Tuple


class TTLCache:
    """
    Thread-safe in-memory cache with TTL (time-to-live) per entry.

    Usage:
        cache = TTLCache(default_ttl=60)
        cache.set("posts:page:1", data, ttl=120)
        data = cache.get("posts:page:1")
        cache.delete("posts:page:1")
        cache.invalidate_prefix("posts:")  # clears all post-related keys
    """

    def __init__(self, default_ttl: int = 60):
        self._store: Dict[str, Tuple[Any, float]] = {}  # {key: (value, expires_at)}
        self._lock = threading.Lock()
        self.default_ttl = default_ttl

    # ── Read ─────────────────────────────────────────────────────────────────

    def get(self, key: str) -> Optional[Any]:
        """Return cached value or None if missing/expired."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    # ── Write ─────────────────────────────────────────────────────────────────

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Store value with TTL (seconds). Uses default_ttl if not specified."""
        expires_at = time.monotonic() + (ttl if ttl is not None else self.default_ttl)
        with self._lock:
            self._store[key] = (value, expires_at)

    # ── Delete ─────────────────────────────────────────────────────────────────

    def delete(self, key: str) -> None:
        """Remove a single key."""
        with self._lock:
            self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with `prefix`. Returns count removed."""
        with self._lock:
            keys_to_remove = [k for k in self._store if k.startswith(prefix)]
            for k in keys_to_remove:
                del self._store[k]
            return len(keys_to_remove)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._store.clear()

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            now = time.monotonic()
            total = len(self._store)
            active = sum(1 for _, (_, exp) in self._store.items() if now <= exp)
            expired = total - active
            return {
                "total_keys": total,
                "active_keys": active,
                "expired_keys": expired,
            }


# ── Global Cache Instances ────────────────────────────────────────────────────

# Posts cache: TTL = 2 minutes
posts_cache = TTLCache(default_ttl=120)

# Comments cache: TTL = 90 seconds
comments_cache = TTLCache(default_ttl=90)
