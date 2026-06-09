"""Tests for AI Spend Watcher CLI."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from spendwatch.cli import main
from spendwatch.config import Config, ensure_config_dir


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_config():
    return Config(api_key="sk-or-v1-test-key")


@pytest.fixture
def mock_generations():
    return [
        {
            "model": "gpt-4o",
            "prompt_tokens": 150,
            "completion_tokens": 80,
            "total_tokens": 230,
            "cost": 0.00115,
            "created_at": "2026-06-09T12:00:00Z",
        },
        {
            "model": "claude-3.5-sonnet",
            "prompt_tokens": 500,
            "completion_tokens": 200,
            "total_tokens": 700,
            "cost": 0.0021,
            "created_at": "2026-06-09T14:30:00Z",
        },
    ]


def test_version(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "spendwatch" in result.output


def test_help(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "daily" in result.output
    assert "total" in result.output
    assert "alert" in result.output
    assert "models" in result.output
    assert "account" in result.output
    assert "init" in result.output
    assert "cache" in result.output


def test_init(runner):
    with patch("spendwatch.cli.ensure_config_dir") as mock_ensure:
        mock_ensure.return_value = Path("/tmp/.spendwatch")
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Config directory created" in result.output


def test_daily_no_api_key(runner):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = Config()
        result = runner.invoke(main, ["daily"])
        assert "No API key configured" in result.output


def test_daily_with_data(runner, mock_config, mock_generations):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = mock_config
        with patch("spendwatch.cli.get_daily_spend") as mock_daily:
            mock_daily.return_value = mock_generations
            result = runner.invoke(main, ["daily"])
            assert result.exit_code == 0
            assert "gpt-4o" in result.output
            assert "claude-3.5-sonnet" in result.output
            assert "TOTAL" in result.output


def test_total_no_api_key(runner):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = Config()
        result = runner.invoke(main, ["total"])
        assert "No API key configured" in result.output


def test_alert_within_limit(runner, mock_config, mock_generations):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = mock_config
        with patch("spendwatch.cli.get_daily_spend") as mock_daily:
            mock_daily.return_value = mock_generations
            result = runner.invoke(main, ["alert", "--limit", "10.00"])
            assert result.exit_code == 0
            assert "Within budget" in result.output


def test_alert_exceeded(runner, mock_config, mock_generations):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = mock_config
        with patch("spendwatch.cli.get_daily_spend") as mock_daily:
            mock_daily.return_value = mock_generations
            result = runner.invoke(main, ["alert", "--limit", "0.001"])
            assert result.exit_code == 1
            assert "SPEND ALERT" in result.output


def test_models_no_api_key(runner):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = Config()
        result = runner.invoke(main, ["models"])
        assert "No API key configured" in result.output


def test_account_no_api_key(runner):
    with patch("spendwatch.cli.load_config") as mock_load:
        mock_load.return_value = Config()
        result = runner.invoke(main, ["account"])
        assert "No API key configured" in result.output


def test_cache(runner):
    result = runner.invoke(main, ["cache"])
    assert result.exit_code == 0
    assert "Cache directory" in result.output
