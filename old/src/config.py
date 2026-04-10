import json
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Optional, List

DEFAULT_LOGS_PATH = str(Path.home() / "Documents" / "My Games" / "StarConflict" / "logs")

def get_root_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        # src/config.py -> src -> SC Nexus (root)
        return Path(__file__).parent.parent

ROOT_DIR = get_root_dir()
USER_DATA_DIR = ROOT_DIR / "user_data"
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = USER_DATA_DIR / "config.json"


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
