"""Tests for the API module."""

from datetime import date
from unittest.mock import patch, MagicMock
import requests

from spendwatch.api import _parse_cost, fetch_generations, get_daily_spend, get_total_spend
from spendwatch.config import Config


def test_parse_cost_known_model():
    cost = _parse_cost(1000, "gpt-4o")
    assert cost == 0.005  # $0.005 per 1K tokens


def test_parse_cost_unknown_model():
    cost = _parse_cost(5000, "unknown-model-xyz")
    assert cost == 0.0


def test_parse_cost_partial_match():
    cost = _parse_cost(2000, "openai/gpt-4o-2024-08-06")
    assert cost == 0.01  # 2000 tokens at $0.005/1K


def test_parse_cost_claude():
    cost = _parse_cost(1000, "claude-3.5-sonnet")
    assert cost == 0.003


def test_parse_cost_deepseek():
    cost = _parse_cost(100000, "deepseek-v4-pro")
    # deepseek-v4 matches 'deepseek-v4' pricing: $0.001/1K
    assert cost == 0.1


def test_fetch_generations_no_api_key():
    config = Config()
    gens = fetch_generations(config)
    assert gens == []


def test_fetch_generations_api_error():
    config = Config(api_key="***")
    with patch("spendwatch.api.requests.get") as mock_get:
        mock_get.side_effect = requests.RequestException("Connection error")
        gens = fetch_generations(config)
        assert gens == []


def test_fetch_generations_success():
    config = Config(api_key="sk-or-v1-test")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {
                "model": "gpt-4o",
                "total_tokens": 500,
                "usage": {"prompt_tokens": 300, "completion_tokens": 200},
                "total_cost": 0.0025,
                "created_at": "2026-06-09T12:00:00Z",
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("spendwatch.api.requests.get") as mock_get:
        mock_get.return_value = mock_response
        gens = fetch_generations(config)
        assert len(gens) == 1
        assert gens[0]["model"] == "gpt-4o"
        assert gens[0]["total_tokens"] == 500
        assert gens[0]["cost"] == 0.0025


def test_fetch_generations_pagination():
    config = Config(api_key="sk-or-v1-test")

    def side_effect(*args, **kwargs):
        page = kwargs["params"]["page"]
        mock = MagicMock()
        if page == 1:
            mock.json.return_value = {"data": [{"model": f"model-{i}", "total_tokens": 100, "total_cost": 0.001, "created_at": "2026-06-09"} for i in range(3)]}
        else:
            mock.json.return_value = {"data": []}
        mock.raise_for_status = MagicMock()
        return mock

    with patch("spendwatch.api.requests.get") as mock_get:
        mock_get.side_effect = side_effect
        gens = fetch_generations(config, limit=3)
        assert len(gens) == 3


def test_get_daily_spend_cache(tmp_path):
    from spendwatch.config import CACHE_DIR
    import spendwatch.api as api_mod

    config = Config(api_key="sk-or-v1-test")

    # Write cache
    cache_file = tmp_path / "spend_2026-06-09.json"
    cache_file.write_text('[{"model": "cached-model", "total_tokens": 100, "cost": 0.001}]')

    with patch.object(api_mod, "CACHE_DIR", tmp_path):
        with patch.object(api_mod, "_load_cache", wraps=api_mod._load_cache) as mock_cache:
            gens = get_daily_spend(config, "2026-06-09", use_cache=True)
            assert len(gens) == 1
            assert gens[0]["model"] == "cached-model"


def test_get_total_spend():
    config = Config(api_key="sk-or-v1-test")
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"model": "gpt-4o", "total_tokens": 100, "total_cost": 0.001, "created_at": "2026-06-01"},
            {"model": "claude-3.5-sonnet", "total_tokens": 200, "total_cost": 0.002, "created_at": "2026-06-05"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("spendwatch.api.requests.get") as mock_get:
        mock_get.return_value = mock_response
        gens = get_total_spend(config, "2026-06-01", "2026-06-09")
        assert len(gens) == 2
