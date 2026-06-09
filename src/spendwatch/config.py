"""Configuration management for AI Spend Watcher.

Reads from ~/.spendwatch/config.toml and OPENROUTER_API_KEY env var.
"""

import os
import tomllib
from pathlib import Path
from dataclasses import dataclass, field


CONFIG_DIR = Path.home() / ".spendwatch"
CONFIG_FILE = CONFIG_DIR / "config.toml"
CACHE_DIR = CONFIG_DIR / "cache"

DEFAULT_CONFIG = """# AI Spend Watcher Configuration
# Place your OpenRouter API key here or set OPENROUTER_API_KEY env var

[openrouter]
# api_key = "sk-or-v1-..."

[budget]
# daily_limit = 5.00
# monthly_limit = 50.00

[display]
# currency = "USD"
"""


@dataclass
class Config:
    api_key: str | None = None
    daily_limit: float | None = None
    monthly_limit: float | None = None
    currency: str = "USD"

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key)


def load_config() -> Config:
    """Load configuration from file and environment."""
    config = Config()

    # Try env var first (highest priority)
    config.api_key = os.environ.get("OPENROUTER_API_KEY")

    # Then try config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "rb") as f:
                data = tomllib.load(f)

            if not config.api_key:
                config.api_key = data.get("openrouter", {}).get("api_key")

            budget = data.get("budget", {})
            config.daily_limit = budget.get("daily_limit")
            config.monthly_limit = budget.get("monthly_limit")

            display = data.get("display", {})
            config.currency = display.get("currency", "USD")
        except Exception:
            pass  # Silently fall back to defaults on parse error

    return config


def ensure_config_dir() -> Path:
    """Create config directory and default config if they don't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(DEFAULT_CONFIG)

    return CONFIG_DIR
