import json
import os

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_settings():

    configured_path = os.environ.get("C_CODE_ANALYZER_CONFIG")

    if configured_path:
        config_path = Path(configured_path).expanduser().resolve()
    else:
        config_path = PROJECT_ROOT / "config" / "settings.json"

    if not config_path.is_file():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}"
        )

    with config_path.open("r", encoding="utf-8") as config_file:
        return json.load(config_file)


SETTINGS = load_settings()


def get_tool_settings(tool_name: str) -> dict:

    return SETTINGS["tools"][tool_name]
