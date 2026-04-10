import json
import os
from pathlib import Path
from typing import Dict, Optional

class DisplayNameManager:
    def __init__(self, config_path: Path):
        self.config_path = config_path / "display_names.json"
        self.mappings: Dict[str, str] = {}
        self.load()

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self.mappings = json.load(f)
            except Exception as e:
                print(f"Error loading display names: {e}")
                self.mappings = {}
        else:
            self.mappings = {}

    def save(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.mappings, f, indent=4, sort_keys=True)
        except Exception as e:
            print(f"Error saving display names: {e}")

    def get_display_name(self, log_name: str) -> str:
        return self.mappings.get(log_name, log_name)

    def set_display_name(self, log_name: str, display_name: str):
        if not display_name:
            if log_name in self.mappings:
                del self.mappings[log_name]
        else:
            self.mappings[log_name] = display_name
        self.save()

    def bulk_update(self, entries: Dict[str, str]) -> int:
        """Apply multiple display-name changes at once. Returns number of updated entries."""
        changed = 0
        for log_name, display_name in entries.items():
            key = (log_name or "").strip()
            if not key:
                continue
            value = (display_name or "").strip()
            if not value:
                if key in self.mappings:
                    del self.mappings[key]
                    changed += 1
                continue
            if self.mappings.get(key) != value:
                self.mappings[key] = value
                changed += 1
        if changed:
            self.save()
        return changed

    def export(self, destination: Path):
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as f:
            json.dump(self.mappings, f, indent=4, sort_keys=True)

    def get_all_mappings(self) -> Dict[str, str]:
        return self.mappings.copy()
