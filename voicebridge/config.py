import json
import os
from dataclasses import asdict, dataclass

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "VoiceBridge")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


@dataclass
class Config:
    auto_enter: bool = True
    model_size: str = "base"
    language: str = "en"
    sample_rate: int = 16000
    silence_ms: int = 700
    min_speech_ms: int = 250

    @classmethod
    def load(cls) -> "Config":
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**{**asdict(cls()), **data})
        return cls()

    def save(self) -> None:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2)
