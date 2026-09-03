"""
CodeSense - Caching Mechanism
Thread-safe in-memory + disk-based LRU cache for analysis results.
"""

import hashlib
import json
import time
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from logger import get_logger

logger = get_logger(__name__)


class LRUCache:
    """Thread-safe in-memory LRU cache with TTL support."""

    def __init__(self, max_size: int = 500, ttl: int = 3600) -> None:
        self.max_size  = max_size
        self.ttl       = ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock     = threading.Lock()
        self.hits      = 0
        self.misses    = 0

    def _is_expired(self, timestamp: float) -> bool:
        return (time.time() - timestamp) > self.ttl

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if key not in self._cache:
                self.misses += 1
                return None
            value, ts = self._cache[key]
            if self._is_expired(ts):
                del self._cache[key]
                self.misses += 1
                return None
            self._cache.move_to_end(key)
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.time())
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    def stats(self) -> dict:
        total = self.hits + self.misses
        return {
            "size":      len(self._cache),
            "max_size":  self.max_size,
            "hits":      self.hits,
            "misses":    self.misses,
            "hit_rate":  f"{(self.hits / total * 100):.1f}%" if total else "0%",
        }


class DiskCache:
    """Persistent disk-based cache with TTL."""

    def __init__(self, directory: str = "cache", ttl: int = 3600) -> None:
        self.directory = Path(directory)
        self.ttl       = ttl
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        safe = hashlib.md5(key.encode()).hexdigest()
        return self.directory / f"{safe}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if (time.time() - data["ts"]) > self.ttl:
                path.unlink(missing_ok=True)
                return None
            return data["value"]
        except Exception as exc:
            logger.debug("Disk cache read error: %s", exc)
            return None

    def set(self, key: str, value: Any) -> None:
        path = self._path(key)
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(
                json.dumps({"ts": time.time(), "value": value}, default=str),
                encoding="utf-8",
            )
            tmp_path.replace(path)
        except Exception as exc:
            logger.debug("Disk cache write error: %s", exc)
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def clear(self) -> None:
        for f in self.directory.glob("*.json"):
            f.unlink(missing_ok=True)

    def purge_expired(self) -> int:
        removed = 0
        for f in self.directory.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if (time.time() - data["ts"]) > self.ttl:
                    f.unlink()
                    removed += 1
            except Exception:
                f.unlink(missing_ok=True)
                removed += 1
        return removed


class AnalysisCache:
    """Two-tier cache (memory + disk) for code analysis results."""

    def __init__(self, directory: str = "cache", ttl: int = 3600,
                 max_memory: int = 500, enabled: bool = True) -> None:
        self.enabled    = enabled
        self.memory     = LRUCache(max_size=max_memory, ttl=ttl)
        self.disk       = DiskCache(directory=directory, ttl=ttl)

    @staticmethod
    def make_key(code: str, language: str, analysis_level: str = "standard") -> str:
        payload = f"{language}:{analysis_level}:{code}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, key: str) -> Optional[dict]:
        if not self.enabled:
            return None
        result = self.memory.get(key)
        if result is not None:
            return result
        result = self.disk.get(key)
        if result is not None:
            self.memory.set(key, result)   # Warm up memory cache
        return result

    def set(self, key: str, value: dict) -> None:
        if not self.enabled:
            return
        self.memory.set(key, value)
        self.disk.set(key, value)

    def invalidate(self, key: str) -> None:
        self.memory.delete(key)
        self.disk.delete(key)

    def clear_all(self) -> None:
        self.memory.clear()
        self.disk.clear()

    def stats(self) -> dict:
        return {"memory": self.memory.stats(), "enabled": self.enabled}


# ─── Module-level singleton ──────────────────────────────────────────────────
_cache_instance: Optional[AnalysisCache] = None


def get_cache() -> AnalysisCache:
    global _cache_instance
    if _cache_instance is None:
        try:
            from config import get_config
            cfg = get_config()
            _cache_instance = AnalysisCache(
                directory=cfg.cache.directory,
                ttl=cfg.cache.ttl,
                max_memory=cfg.cache.max_size,
                enabled=cfg.cache.enabled,
            )
        except Exception:
            _cache_instance = AnalysisCache()
    return _cache_instance