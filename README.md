# AI Spend Watcher 💸

Track your AI API spending across providers from the command line.

**Primary provider: [OpenRouter](https://openrouter.ai)** — monitor your generation
costs, credit usage, and model breakdowns with a single command.

## Features

- **`spendwatch daily`** — Today's spend broken down by model
- **`spendwatch total`** — Total spend across any timeframe
- **`spendwatch alert`** — Get alerted when spend exceeds a budget limit
- **`spendwatch models`** — Cost-per-model breakdown with percentages
- **`spendwatch account`** — View OpenRouter credits and rate limits
- **`spendwatch cache`** — View or clear local cache
- Offline viewing with local JSON cache
- Beautiful terminal output with [Rich](https://github.com/Textualize/rich)

## Installation

```bash
# Install with pip
pip install git+https://github.com/danbirker-svg/ai-spend-watcher.git

# Or clone and install in development mode
git clone https://github.com/danbirker-svg/ai-spend-watcher.git
cd ai-spend-watcher
pip install -e .
```

## Quick Start

### 1. Initialize config

```bash
spendwatch init
```

This creates `~/.spendwatch/config.toml` with a default template.

### 2. Configure your API key

Either set the environment variable:

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Or edit the config file:

```toml
# ~/.spendwatch/config.toml
[openrouter]
api_key = "sk-or-v1-..."
```

### 3. Check your spending

```bash
# Today's spend by model
spendwatch daily

# Total spend last 30 days
spendwatch total

# Set a budget alert
spendwatch alert --limit 5.00

# Cost per model
spendwatch models

# Account info
spendwatch account
```

## Usage

```
Usage: spendwatch [OPTIONS] COMMAND [ARGS]...

  AI Spend Watcher — Track your AI API spending across providers.

Commands:
  daily    Show today's spend by model
  total    Show total spend across a timeframe
  alert    Alert if spend exceeds a specified limit
  models   Show cost breakdown by model
  account  Show OpenRouter account info (credits, rate limits)
  init     Initialize config directory and default config file
  cache    Show or clear cache
```

### `spendwatch daily`

```bash
# Today's spend
spendwatch daily

# Specific date
spendwatch daily --date 2026-06-01

# Force fresh fetch (skip cache)
spendwatch daily --no-cache
```

### `spendwatch total`

```bash
# Last 30 days
spendwatch total

# Custom range
spendwatch total --from 2026-01-01 --to 2026-06-09

# Shorthand
spendwatch total -f 2026-06-01 -t 2026-06-09
```

### `spendwatch alert`

```bash
# Alert if today's spend exceeds $5
spendwatch alert --limit 5.00

# Check specific date
spendwatch alert --limit 10.00 --date 2026-06-01

# Exits with code 1 if limit exceeded (useful in scripts)
spendwatch alert --limit 5.00 && echo "Budget OK"
```

### `spendwatch models`

```bash
# All models in last 30 days
spendwatch models

# Custom range
spendwatch models --from 2026-01-01 --to 2026-06-09
```

### `spendwatch account`

```bash
# Show credits and rate limits
spendwatch account
```

### `spendwatch cache`

```bash
# Show cache stats
spendwatch cache

# Clear cache
spendwatch cache --clear
```

## Configuration

Full config options in `~/.spendwatch/config.toml`:

```toml
[openrouter]
api_key = "sk-or-v1-..."

[budget]
daily_limit = 5.00
monthly_limit = 50.00

[display]
currency = "USD"
```

| Option | Env Var | Description |
|--------|---------|-------------|
| `openrouter.api_key` | `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `budget.daily_limit` | — | Daily budget for reference |
| `budget.monthly_limit` | — | Monthly budget for reference |
| `display.currency` | — | Currency display (default: USD) |

Environment variables take precedence over config file values.

## Requirements

- Python 3.11+
- An [OpenRouter](https://openrouter.ai) account and API key

## Development

```bash
# Clone and install dev dependencies
git clone https://github.com/danbirker-svg/ai-spend-watcher.git
cd ai-spend-watcher
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with coverage
pytest --cov=spendwatch
```

## License

MIT — see [LICENSE](LICENSE)
