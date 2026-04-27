import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


DEFAULT_TRIGGER_KEY = "ctrl_r"
DEFAULT_MODE = "hold"
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_AUTO_PASTE = False
DEFAULT_MODEL = "gpt-4o-transcribe"
VALID_MODES = {"hold", "toggle"}


@dataclass
class AppConfig:
    openai_api_key: str
    trigger_key: str = DEFAULT_TRIGGER_KEY
    mode: str = DEFAULT_MODE
    sample_rate: int = DEFAULT_SAMPLE_RATE
    auto_paste: bool = DEFAULT_AUTO_PASTE
    model: str = DEFAULT_MODEL

    @property
    def is_hold_mode(self) -> bool:
        return self.mode == "hold"


def _load_from_file(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_config(config_path: str | Path = "config.json") -> AppConfig:
    path = Path(config_path)
    data = _load_from_file(path)

    env = os.environ
    trigger_key = env.get("VOICE_INPUT_TRIGGER", data.get("trigger_key", DEFAULT_TRIGGER_KEY))
    mode = env.get("VOICE_INPUT_MODE", data.get("mode", DEFAULT_MODE)).lower()
    sample_rate_raw = env.get("VOICE_INPUT_SAMPLE_RATE", data.get("sample_rate", DEFAULT_SAMPLE_RATE))
    auto_paste_raw = env.get("VOICE_INPUT_AUTO_PASTE", data.get("auto_paste", DEFAULT_AUTO_PASTE))
    model = env.get("VOICE_INPUT_MODEL", data.get("model", DEFAULT_MODEL))

    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Use one of: {', '.join(sorted(VALID_MODES))}.")

    try:
        sample_rate = int(sample_rate_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid sample rate '{sample_rate_raw}'.") from exc

    def parse_bool(val) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            lowered = val.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        raise ValueError(f"Invalid boolean value '{val}'. Use true/false.")

    try:
        auto_paste = parse_bool(auto_paste_raw)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    api_key = env.get("OPENAI_API_KEY") or data.get("openai_api_key")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not set. Set env var or provide in config.json as openai_api_key.")

    return AppConfig(
        openai_api_key=api_key,
        trigger_key=trigger_key,
        mode=mode,
        sample_rate=sample_rate,
        auto_paste=auto_paste,
        model=model,
    )
