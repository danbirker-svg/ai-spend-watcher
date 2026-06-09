# AI Spend Watcher 💸 + 🛡️

Track your AI API spending **and service trust** from the command line.

**Primary provider: [OpenRouter](https://openrouter.ai)** — monitor generation costs, credit usage, and model breakdowns. **Plus: the AI Trust Dashboard** — track paid AI services (ChatGPT, Claude, Manus, Cursor, etc.) for outages, billing issues, and reliability. Because a $400/mo AI tool that silently fails isn't just expensive — it's a liability.

## Features

### 💸 Spend Tracking
- **`spendwatch daily`** — Today's spend broken down by model
- **`spendwatch total`** — Total spend across any timeframe
- **`spendwatch alert`** — Get alerted when spend exceeds a budget limit
- **`spendwatch models`** — Cost-per-model breakdown with percentages
- **`spendwatch account`** — View OpenRouter credits and rate limits

### 🛡️ AI Trust Dashboard (NEW in v0.2)
- **`spendwatch trust check`** — Full health check on all your AI services (status pages, incidents, trust scores)
- **`spendwatch trust add <service>`** — Start tracking any AI service
- **`spendwatch trust costs`** — Total monthly AI subscription spend
- **`spendwatch trust incident`** — Log when a service fails or overcharges
- **Trust scores (1-10)** — Based on status page transparency, uptime, and incident history
- **9 known services** — ChatGPT, Claude, Manus AI, Gemini, Perplexity, Cursor, Codex CLI, Claude Code, Hermes Agent

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

### 2. Configure your API key

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
```

Or edit `~/.spendwatch/config.toml`.

### 3. Check spending

```bash
spendwatch daily          # Today's spend by model
spendwatch total          # Last 30 days
spendwatch alert --limit 5.00  # Budget alert
spendwatch models         # Cost per model
spendwatch account        # Credits & rate limits
```

### 4. Check AI service trust

```bash
spendwatch trust list     # See all known services
spendwatch trust add manus --tier pro   # Track Manus AI ($400/mo)
spendwatch trust check    # Full trust dashboard
```

## AI Trust Dashboard

```bash
# Add services to track
spendwatch trust add chatgpt
spendwatch trust add claude
spendwatch trust add manus --tier pro
spendwatch trust add cursor
spendwatch trust add perplexity

# Run a full health check
spendwatch trust check
```

Example output:

```
🛡️  AI Trust Dashboard
Monthly subscription spend: $460.00  |  Services tracked: 5  |  Avg trust score: 7.2/10

⚠ AT RISK: Manus AI

Tracked AI Services
╭──────────────────┬──────────────┬─────────┬───────┬─────────────────┬──────────────╮
│ Service          │ Status       │ Cost/mo │ Trust │ Incidents (30d) │ Transparency │
├──────────────────┼──────────────┼─────────┼───────┼─────────────────┼──────────────┤
│ Manus AI         │ ◐ DEGRADED   │ $400.00 │ 2/10  │ 3               │ 📊 Public    │
│ ChatGPT / OpenAI │ ● UP         │  $20.00 │ 9/10  │ —               │ 📊 Public    │
│ Claude /Anthropic│ ● UP         │  $20.00 │ 9/10  │ —               │ 📊 Public    │
╰──────────────────┴──────────────┴─────────┴───────┴─────────────────┴──────────────╯
```

### Log an incident

```bash
spendwatch trust incident manus "Charged $400 but agent execution failed silently"
spendwatch trust incident cursor "Composer kept applying changes to wrong file"
```

### Track total subscription costs

```bash
spendwatch trust costs
# Shows: ChatGPT $20 + Claude $20 + Manus $400 = $440/mo
# Plus API costs tracked via spendwatch daily/total
```

## Usage

```
Commands:
  account     Show OpenRouter account info (credits, rate limits)
  alert       Alert if spend exceeds a specified limit
  cache       Show or clear cache
  daily       Show today's spend by model
  init        Initialize config directory and default config file
  models      Show cost breakdown by model
  total       Show total spend across a timeframe
  trust       AI Trust Dashboard — monitor service health, reliability, and billing fairness

Trust Commands:
  add         Add an AI service to your trust tracking
  check       Run a full trust check on all tracked services
  costs       Show total monthly AI subscription spend
  incident    Log an incident for a tracked service
  list        List all known AI services available to track
  remove      Stop tracking a service
```

## Known Services

| Service | Category | Tiers |
|---------|----------|-------|
| ChatGPT / OpenAI | Chat | Plus ($20), Pro ($200) |
| Claude / Anthropic | Chat | Pro ($20), Max ($100), Team ($25) |
| Manus AI | Agent | Starter ($40), Pro ($400) |
| Gemini / Google | Chat | Advanced ($20) |
| Perplexity | Search | Pro ($20) |
| Cursor | IDE | Pro ($20) |
| OpenAI Codex CLI | Agent | Pay-per-use |
| Claude Code | Agent | Pay-per-use |
| Hermes Agent | Agent | Self-hosted |

## Configuration

```toml
# ~/.spendwatch/config.toml
[openrouter]
api_key = "sk-or-v1-..."

[budget]
daily_limit = 5.00
monthly_limit = 50.00

[display]
currency = "USD"
```

## Why Track AI Service Trust?

The Manus AI chargeback situation (June 2026) is the canary in the coal mine. People are paying $200-400/mo for AI tools that silently fail, degrade, or overcharge. Most users don't track this systematically — they just get frustrated and leave.

**AI Spend Watcher + Trust Dashboard** gives you:
- **Spend awareness** — Know exactly what you're paying across all AI tools
- **Reliability tracking** — Catch services that degrade before you waste more money
- **Trust scores** — Quantify which services are actually reliable
- **Incident history** — Data when you need to dispute charges or switch providers

## Requirements

- Python 3.11+
- An [OpenRouter](https://openrouter.ai) account and API key (for spend tracking)

## Development

```bash
git clone https://github.com/danbirker-svg/ai-spend-watcher.git
cd ai-spend-watcher
pip install -e ".[dev]"
pytest              # 27 tests
pytest --cov=spendwatch
```

## License

MIT — see [LICENSE](LICENSE)
