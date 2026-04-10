"""
CacheManager — pickle-based fight cache keyed by (path, mtime, size).

Caches parsed Fight lists so unchanged log files are not re-parsed on
every app launch.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import NamedTuple

from src.core.config import USER_DATA_DIR

# Bump this whenever the Fight/CombatEvent dataclass schema changes.
CACHE_VERSION = 3

_CACHE_FILE = USER_DATA_DIR / "combat_cache.pkl"


class _CacheKey(NamedTuple):
    path:    str
    mtime:   float
    size:    int
    version: int


class CacheManager:
    """
    Persistent fight cache.

    Usage::

        cache = CacheManager()
        fights = cache.get(log_path)
        if fights is None:
            fights = <parse>
            cache.put(log_path, fights)
        cache.flush()
    """

    def __init__(self) -> None:
        self._data: dict[_CacheKey, list] = {}
        self._dirty: bool = False
        self._load()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get(self, log_path: Path) -> list | None:
        key = self._key(log_path)
        if key is None:
            return None
        return self._data.get(key)

    def put(self, log_path: Path, fights: list) -> None:
        key = self._key(log_path)
        if key is None:
            return
        self._data[key] = fights
        self._dirty = True

    def clear(self) -> None:
        self._data.clear()
        self._dirty = True
        self.flush()

    def flush(self) -> None:
        if not self._dirty:
            return
        try:
            USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
            _CACHE_FILE.write_bytes(pickle.dumps(self._data, protocol=5))
            self._dirty = False
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _key(self, path: Path) -> _CacheKey | None:
        try:
            stat = path.stat()
            return _CacheKey(str(path), stat.st_mtime, stat.st_size, CACHE_VERSION)
        except OSError:
            return None

    def _load(self) -> None:
        try:
            if _CACHE_FILE.exists():
                loaded = pickle.loads(_CACHE_FILE.read_bytes())
                if isinstance(loaded, dict):
                    # Drop entries from older cache versions automatically
                    self._data = {
                        k: v for k, v in loaded.items()
                        if isinstance(k, _CacheKey) and k.version == CACHE_VERSION
                    }
        except Exception:
            self._data = {}
