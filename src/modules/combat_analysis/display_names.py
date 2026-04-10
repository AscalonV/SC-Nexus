"""Legacy-compatible display-name manager.

Supports both the old flat JSON format and the newer wrapped {"mappings": {...}}
format so existing display_names.json files continue to work.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.core.config import ROOT_DIR, USER_DATA_DIR


class DisplayNameManager:
    def __init__(self, config_path: Path | None = None) -> None:
        root = Path(config_path) if config_path is not None else USER_DATA_DIR
        self.config_path = root / "display_names.json"
        self.mappings: dict[str, str] = {}
        self.load()

    def load(self) -> None:
        self.mappings = {}
        try:
            candidate_paths = [self.config_path, ROOT_DIR / "old" / "user_data" / "display_names.json"]
            for path in candidate_paths:
                if not path.exists():
                    continue
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and isinstance(data.get("mappings"), dict):
                    data = data["mappings"]
                if not isinstance(data, dict):
                    continue
                for log_name, display_name in data.items():
                    key = str(log_name).strip()
                    value = str(display_name).strip()
                    if key:
                        self.mappings[key] = value
                if self.mappings:
                    break
        except Exception:
            self.mappings = {}

    def save(self) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(
            json.dumps(self.mappings, indent=4, sort_keys=True),
            encoding="utf-8",
        )

    def get(self, log_name: str) -> str:
        return self.get_display_name(log_name)

    def get_display_name(self, log_name: str) -> str:
        mapped = self.mappings.get(log_name)
        return mapped if mapped else log_name

    def set(self, log_name: str, display_name: str) -> None:
        self._set_mapping(log_name, display_name)

    def set_display_name(self, log_name: str, display_name: str) -> None:
        self._set_mapping(log_name, display_name)
        self.save()

    def _set_mapping(self, log_name: str, display_name: str) -> None:
        key = (log_name or "").strip()
        if not key:
            return
        value = (display_name or "").strip()
        if not value or value == key:
            self.mappings.pop(key, None)
        else:
            self.mappings[key] = value

    def bulk_update(self, entries: dict[str, str]) -> int:
        changed = 0
        for log_name, display_name in entries.items():
            key = (log_name or "").strip()
            if not key:
                continue
            old = self.mappings.get(key)
            self._set_mapping(key, display_name)
            new = self.mappings.get(key)
            if old != new:
                changed += 1
        if changed:
            self.save()
        return changed

    def get_all(self) -> dict[str, str]:
        return dict(self.mappings)

    def get_all_mappings(self) -> dict[str, str]:
        return dict(self.mappings)

    def export(self, destination: Path) -> None:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(self.mappings, indent=4, sort_keys=True),
            encoding="utf-8",
        )
