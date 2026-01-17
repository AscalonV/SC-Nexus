import json
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, List

DEFAULT_LOGS_PATH = str(Path.home() / "Documents" / "My Games" / "StarConflict" / "logs")
CONFIG_FILE = Path(__file__).parent / "config.json"


@dataclass
class AppConfig:
    logs_path: str = DEFAULT_LOGS_PATH
    username: str = ""
    disabled_game_modes: List[str] = field(default_factory=list)

    @classmethod
    def load(cls) -> "AppConfig":
        try:
            if CONFIG_FILE.exists():
                data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                return cls(**data)
        except Exception:
            pass
        return cls()

    def save(self) -> None:
        CONFIG_FILE.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
