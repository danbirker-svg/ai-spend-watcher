"""OpenRouter API client for fetching spend/generation data."""

import json
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any

import requests

from .config import CACHE_DIR, Config

OR_BASE = "https://openrouter.ai/api/v1"
GENERATION_URL = f"{OR_BASE}/generation"
KEYS_URL = f"{OR_BASE}/keys"

# Generation data shape we return
# List of dicts with: model, prompt_tokens, completion_tokens, total_tokens, cost, created_at


def _build_headers(config: Config) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }


def _parse_cost(total_tokens: int, model: str) -> float:
    """Estimate cost from token counts and model pricing.
    Uses approximate pricing. Falls back to 0.0 if unknown.
    """
    # Approximate pricing per 1K tokens (blended input/output)
    PRICING: dict[str, float] = {
        # Anthropic
        "claude-3-opus": 0.015,
        "claude-3.5-sonnet": 0.003,
        "claude-3.5-haiku": 0.001,
        "claude-4-sonnet": 0.003,
        "claude-4-opus": 0.015,
        # OpenAI
        "gpt-4o": 0.005,
        "gpt-4-turbo": 0.01,
        "gpt-4": 0.03,
        "gpt-3.5-turbo": 0.0005,
        "o1": 0.015,
        "o1-mini": 0.003,
        "o3-mini": 0.001,
        "gpt-4.1": 0.002,
        # Google
        "gemini-2.5-pro": 0.00375,
        "gemini-2.5-flash": 0.0003,
        "gemini-2.0-flash": 0.0001,
        "gemini-1.5-pro": 0.0035,
        "gemini-1.5-flash": 0.000075,
        # Meta
        "llama-4-maverick": 0.0002,
        "llama-4-scout": 0.0001,
        "llama-3.3-70b": 0.00015,
        "llama-3.1-8b": 0.00002,
        # DeepSeek
        "deepseek-v3": 0.00089,
        "deepseek-v4": 0.001,
        "deepseek-r1": 0.002,
        # Mistral
        "mistral-large": 0.002,
        "mistral-medium": 0.001,
        "mixtral-8x7b": 0.00024,
        # Qwen
        "qwen-max": 0.003,
        "qwen-2.5-72b": 0.00035,
    }

    # Find best match
    model_lower = model.lower()
    best_price = 0.0
    best_len = 0
    for key, price in PRICING.items():
        if key in model_lower and len(key) > best_len:
            best_price = price
            best_len = len(key)

    return round((total_tokens / 1000) * best_price, 6)


def fetch_generations(
    config: Config,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Fetch generation data from OpenRouter API.

    Args:
        config: Config with API key
        from_date: Start date in YYYY-MM-DD format
        to_date: End date in YYYY-MM-DD format
        limit: Max results per page

    Returns:
        List of generation records with model, tokens, cost
    """
    all_generations = []
    page = 1

    params: dict[str, Any] = {"limit": limit, "page": page}
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    while True:
        params["page"] = page
        try:
            resp = requests.get(
                GENERATION_URL,
                headers=_build_headers(config),
                params=params,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
            gens = data.get("data", [])
            if not gens:
                break

            for gen in gens:
                model = gen.get("model", "unknown")
                total_tokens = gen.get("total_tokens", 0)
                usage = gen.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0
                completion_tokens = usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0
                cost = gen.get("total_cost", 0) or _parse_cost(total_tokens, model)

                all_generations.append({
                    "model": model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "cost": float(cost),
                    "created_at": gen.get("created_at", ""),
                })

            # Check pagination
            if len(gens) < limit:
                break
            page += 1

        except requests.RequestException:
            break

    return all_generations


def fetch_credit_info(config: Config) -> dict[str, Any]:
    """Fetch credit/rate-limit info from OpenRouter keys endpoint."""
    try:
        resp = requests.get(
            KEYS_URL,
            headers=_build_headers(config),
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        keys = data.get("data", [])
        if keys:
            key_info = keys[0]
            return {
                "credits_remaining": key_info.get("credits", 0),
                "credits_used": key_info.get("usage", 0),
                "rate_limit_requests": key_info.get("rate_limit", {}).get("requests", 0),
                "rate_limit_interval": key_info.get("rate_limit", {}).get("interval", ""),
                "key_name": key_info.get("name", "Unknown"),
                "is_disabled": key_info.get("disabled", False),
            }
    except requests.RequestException:
        pass

    return {}


def get_daily_spend(
    config: Config,
    target_date: str | None = None,
    use_cache: bool = True,
) -> list[dict[str, Any]]:
    """Get spend for a specific day."""
    if target_date is None:
        target_date = date.today().isoformat()

    if use_cache:
        cached = _load_cache(target_date)
        if cached is not None:
            return cached

    generations = fetch_generations(config, from_date=target_date, to_date=target_date)
    _save_cache(target_date, generations)
    return generations


def get_total_spend(
    config: Config,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict[str, Any]]:
    """Get total spend across a timeframe."""
    if from_date is None:
        from_date = (date.today() - timedelta(days=30)).isoformat()
    if to_date is None:
        to_date = date.today().isoformat()

    generations = fetch_generations(config, from_date=from_date, to_date=to_date)
    return generations


def _cache_path(target_date: str) -> Path:
    return CACHE_DIR / f"spend_{target_date}.json"


def _load_cache(target_date: str) -> list[dict[str, Any]] | None:
    cache_file = _cache_path(target_date)
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
            # Only use cache if it's from today or was cached recently
            return data
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_cache(target_date: str, data: list[dict[str, Any]]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(target_date)
    cache_file.write_text(json.dumps(data, indent=2))
