"""AI Service Trust & Health Monitoring.

Tracks reliability, billing fairness, and transparency of paid AI services.
The "Trust Dashboard" — because a $400/mo AI tool that silently fails isn't
just expensive, it's a liability.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
import json
import os

import requests

from .config import ensure_config_dir

# ── Known AI services ──────────────────────────────────────────────

KNOWN_SERVICES: dict[str, dict[str, Any]] = {
    "manus": {
        "name": "Manus AI",
        "url": "https://manus.im",
        "status_url": "https://status.manus.im",
        "tier_pricing": {"starter": 40, "pro": 400},
        "category": "agent",
    },
    "chatgpt": {
        "name": "ChatGPT / OpenAI",
        "url": "https://chatgpt.com",
        "status_url": "https://status.openai.com",
        "tier_pricing": {"plus": 20, "pro": 200},
        "category": "chat",
    },
    "claude": {
        "name": "Claude / Anthropic",
        "url": "https://claude.ai",
        "status_url": "https://status.anthropic.com",
        "tier_pricing": {"pro": 20, "max": 100, "team": 25},
        "category": "chat",
    },
    "gemini": {
        "name": "Gemini / Google",
        "url": "https://gemini.google.com",
        "status_url": "https://www.google.com/appsstatus",
        "tier_pricing": {"advanced": 20},
        "category": "chat",
    },
    "perplexity": {
        "name": "Perplexity",
        "url": "https://perplexity.ai",
        "status_url": "https://status.perplexity.ai",
        "tier_pricing": {"pro": 20},
        "category": "search",
    },
    "cursor": {
        "name": "Cursor",
        "url": "https://cursor.com",
        "status_url": "https://status.cursor.com",
        "tier_pricing": {"pro": 20},
        "category": "ide",
    },
    "codex": {
        "name": "OpenAI Codex CLI",
        "url": "https://github.com/openai/codex",
        "status_url": None,
        "tier_pricing": {"usage": 0},  # pay-per-use
        "category": "agent",
    },
    "claude-code": {
        "name": "Claude Code",
        "url": "https://claude.ai",
        "status_url": "https://status.anthropic.com",
        "tier_pricing": {"usage": 0},
        "category": "agent",
    },
    "hermes": {
        "name": "Hermes Agent",
        "url": "https://hermes-agent.nousresearch.com",
        "status_url": None,
        "tier_pricing": {"self_hosted": 0},
        "category": "agent",
    },
}


@dataclass
class ServiceHealth:
    """Health status for a single AI service."""
    service_id: str
    name: str
    url: str
    category: str
    subscription_cost: float
    # Status
    is_up: bool = True
    status_detail: str = ""
    # History
    incidents_30d: int = 0
    avg_response_time_ms: float = 0
    last_checked: str = ""
    # Trust signals
    has_public_status_page: bool = False
    has_refund_policy: bool = True
    transparency_score: int = 5  # 1-10
    # User notes
    user_rating: int = 0  # 1-5
    notes: str = ""


@dataclass
class TrustReport:
    """Full trust dashboard report."""
    services: list[ServiceHealth] = field(default_factory=list)
    generated_at: str = ""
    total_monthly_spend: float = 0
    at_risk_services: list[str] = field(default_factory=list)
    trust_score_avg: float = 0


def get_services_file() -> Path:
    """Get path to tracked services JSON file."""
    config_dir = ensure_config_dir()
    return config_dir / "services.json"


def load_services() -> dict[str, dict[str, Any]]:
    """Load user's tracked services from config."""
    services_file = get_services_file()
    if not services_file.exists():
        # Default: track common services
        defaults = {
            "chatgpt": {"subscription": "plus", "monthly_cost": 20},
            "claude": {"subscription": "pro", "monthly_cost": 20},
        }
        save_services(defaults)
        return defaults

    with open(services_file) as f:
        return json.load(f)


def save_services(services: dict[str, dict[str, Any]]) -> None:
    """Save tracked services to config."""
    services_file = get_services_file()
    services_file.parent.mkdir(parents=True, exist_ok=True)
    with open(services_file, "w") as f:
        json.dump(services, f, indent=2)


def add_service(service_id: str, subscription: str = "pro") -> bool:
    """Add a service to tracking. Returns True if added, False if already tracked."""
    service_id = service_id.lower()

    if service_id not in KNOWN_SERVICES:
        return False

    services = load_services()
    if service_id in services:
        return False

    info = KNOWN_SERVICES[service_id]
    tier = info["tier_pricing"].get(subscription, list(info["tier_pricing"].values())[0])

    services[service_id] = {
        "subscription": subscription,
        "monthly_cost": tier,
        "added_at": datetime.utcnow().isoformat(),
        "incidents": [],
    }
    save_services(services)
    return True


def remove_service(service_id: str) -> bool:
    """Remove a service from tracking."""
    services = load_services()
    if service_id.lower() not in services:
        return False
    del services[service_id.lower()]
    save_services(services)
    return True


def check_service_status(service_id: str) -> str:
    """Check a service's public status page. Returns status string.

    Tries common status API patterns:
    - /api/v2/status.json (Atlassian-style)
    - /api/v2/summary.json
    - Simple HTTP check
    """
    info = KNOWN_SERVICES.get(service_id.lower())
    if not info or not info.get("status_url"):
        return "unknown"

    status_url = info["status_url"]

    try:
        # Try standard status API
        resp = requests.get(f"{status_url}/api/v2/status.json", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            indicator = data.get("status", {}).get("indicator", "")
            if indicator == "none":
                return "operational"
            elif indicator in ("minor", "major"):
                return "degraded"
            elif indicator == "critical":
                return "down"
            return indicator or "operational"
    except Exception:
        pass

    try:
        # Try summary endpoint
        resp = requests.get(f"{status_url}/api/v2/summary.json", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            components = data.get("components", [])
            degraded = [c for c in components if c.get("status") not in ("operational",)]
            if not degraded:
                return "operational"
            if any(c.get("status") == "major_outage" for c in degraded):
                return "down"
            return "degraded"
    except Exception:
        pass

    # Fallback: simple HTTP check
    try:
        resp = requests.get(status_url, timeout=5)
        if resp.status_code < 500:
            return "operational"
        return "degraded"
    except Exception:
        return "unknown"


def check_all_services() -> TrustReport:
    """Check status of all tracked services and build a trust report."""
    services = load_services()
    results: list[ServiceHealth] = []
    total_spend = 0.0
    at_risk: list[str] = []

    for service_id, user_config in services.items():
        info = KNOWN_SERVICES.get(service_id)
        if not info:
            continue

        monthly_cost = user_config.get("monthly_cost", 0)
        total_spend += monthly_cost

        status = check_service_status(service_id)
        is_up = status in ("operational", "unknown")

        # Calculate trust score
        trust = 5  # baseline
        has_status_page = bool(info.get("status_url"))
        if has_status_page:
            trust += 2
        if is_up:
            trust += 2
        else:
            trust -= 3
        if status == "down":
            trust -= 2

        trust = max(1, min(10, trust))

        # Load incidents
        incidents = user_config.get("incidents", [])
        recent_incidents = [
            i for i in incidents
            if datetime.fromisoformat(i["date"]) > datetime.utcnow() - timedelta(days=30)
        ]

        health = ServiceHealth(
            service_id=service_id,
            name=info["name"],
            url=info["url"],
            category=info.get("category", "other"),
            subscription_cost=monthly_cost,
            is_up=is_up,
            status_detail=status,
            incidents_30d=len(recent_incidents),
            last_checked=datetime.utcnow().isoformat(),
            has_public_status_page=has_status_page,
            transparency_score=trust if has_status_page else trust - 1,
            user_rating=user_config.get("rating", 0),
            notes=user_config.get("notes", ""),
        )

        if trust <= 3 or status == "down":
            at_risk.append(service_id)

        results.append(health)

    # Calculate average trust score
    avg_trust = sum(s.transparency_score for s in results) / len(results) if results else 0

    return TrustReport(
        services=results,
        generated_at=datetime.utcnow().isoformat(),
        total_monthly_spend=total_spend,
        at_risk_services=at_risk,
        trust_score_avg=avg_trust,
    )


def log_incident(service_id: str, description: str) -> None:
    """Log an incident for a service."""
    services = load_services()
    if service_id not in services:
        return

    incident = {
        "date": datetime.utcnow().isoformat(),
        "description": description,
    }
    services[service_id].setdefault("incidents", []).append(incident)
    # Keep only last 50 incidents
    services[service_id]["incidents"] = services[service_id]["incidents"][-50:]
    save_services(services)


def list_known_services() -> list[dict[str, Any]]:
    """Return list of all known services the user can track."""
    tracked = load_services()
    result = []
    for sid, info in KNOWN_SERVICES.items():
        tiers = info.get("tier_pricing", {})
        result.append({
            "id": sid,
            "name": info["name"],
            "url": info["url"],
            "category": info.get("category", "other"),
            "status_url": info.get("status_url"),
            "tiers": tiers,
            "tracked": sid in tracked,
        })
    return sorted(result, key=lambda x: x["name"])
