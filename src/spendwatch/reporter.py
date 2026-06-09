"""Rich terminal output for AI Spend Watcher — extended with Trust Dashboard."""

from collections import defaultdict
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.layout import Layout
from rich.align import Align

from .trust import TrustReport, ServiceHealth, list_known_services

console = Console()


def _format_cost(cost: float) -> str:
    return f"${cost:.4f}"


def _status_icon(is_up: bool, status_detail: str) -> str:
    """Return a Rich-styled status indicator."""
    if status_detail == "down":
        return "[bold red]● DOWN[/bold red]"
    elif status_detail == "degraded":
        return "[yellow]◐ DEGRADED[/yellow]"
    elif is_up:
        return "[green]● UP[/green]"
    return "[dim]◌ UNKNOWN[/dim]"


def _trust_color(score: int) -> str:
    """Get color for trust score."""
    if score >= 8:
        return "green"
    elif score >= 5:
        return "yellow"
    else:
        return "red"


# ── Spend Reports (existing) ────────────────────────────────────────

def report_daily(generations: list[dict[str, Any]], target_date: str) -> None:
    """Display daily spend breakdown by model."""
    if not generations:
        console.print(
            Panel(
                f"[yellow]No spend data found for {target_date}[/yellow]\n"
                "Make sure your API key is configured and has recent usage.",
                title="Daily Spend",
                border_style="yellow",
            )
        )
        return

    total = sum(g["cost"] for g in generations)
    total_tokens = sum(g["total_tokens"] for g in generations)

    by_model: dict[str, dict] = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
    for gen in generations:
        m = by_model[gen["model"]]
        m["cost"] += gen["cost"]
        m["tokens"] += gen["total_tokens"]
        m["calls"] += 1

    table = Table(title=f"Daily Spend — {target_date}", box=box.ROUNDED)
    table.add_column("Model", style="cyan", no_wrap=True)
    table.add_column("Calls", justify="right", style="dim")
    table.add_column("Tokens", justify="right")
    table.add_column("Cost", justify="right", style="green")

    for model, data in sorted(by_model.items(), key=lambda x: x[1]["cost"], reverse=True):
        table.add_row(
            model,
            str(data["calls"]),
            f"{data['tokens']:,}",
            _format_cost(data["cost"]),
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{len(generations)}[/bold]",
        f"[bold]{total_tokens:,}[/bold]",
        f"[bold green]{_format_cost(total)}[/bold green]",
    )

    console.print(table)


def report_total(generations: list[dict[str, Any]], from_date: str, to_date: str) -> None:
    """Display total spend over a timeframe."""
    if not generations:
        console.print(
            Panel(
                f"[yellow]No spend data found for {from_date} to {to_date}[/yellow]",
                title="Total Spend",
                border_style="yellow",
            )
        )
        return

    total_cost = sum(g["cost"] for g in generations)
    total_tokens = sum(g["total_tokens"] for g in generations)
    total_calls = len(generations)

    by_day: dict[str, float] = defaultdict(float)
    for gen in generations:
        day = gen["created_at"][:10] if gen["created_at"] else "unknown"
        by_day[day] += gen["cost"]

    summary = Text()
    summary.append("Total Calls: ", style="dim")
    summary.append(f"{total_calls:,}\n", style="bold")
    summary.append("Total Tokens: ", style="dim")
    summary.append(f"{total_tokens:,}\n", style="bold")
    summary.append("Total Cost: ", style="dim")
    summary.append(_format_cost(total_cost), style="bold green")

    console.print(Panel(summary, title=f"Total Spend — {from_date} to {to_date}", border_style="blue"))

    if len(by_day) > 1:
        table = Table(title="Daily Breakdown", box=box.SIMPLE)
        table.add_column("Date", style="cyan")
        table.add_column("Cost", justify="right", style="green")

        for day, cost in sorted(by_day.items()):
            table.add_row(day, _format_cost(cost))

        console.print()
        console.print(table)


def report_models(generations: list[dict[str, Any]]) -> None:
    """Display cost breakdown by model."""
    if not generations:
        console.print(
            Panel("[yellow]No data to display[/yellow]", title="Model Breakdown", border_style="yellow")
        )
        return

    by_model: dict[str, dict] = defaultdict(lambda: {
        "cost": 0.0,
        "tokens": 0,
        "calls": 0,
        "avg_cost_per_call": 0.0,
    })

    for gen in generations:
        m = by_model[gen["model"]]
        m["cost"] += gen["cost"]
        m["tokens"] += gen["total_tokens"]
        m["calls"] += 1

    for model, data in by_model.items():
        data["avg_cost_per_call"] = data["cost"] / data["calls"] if data["calls"] else 0

    total_cost = sum(v["cost"] for v in by_model.values())

    table = Table(title="Cost Per Model", box=box.ROUNDED)
    table.add_column("Model", style="cyan")
    table.add_column("Calls", justify="right", style="dim")
    table.add_column("Total Cost", justify="right", style="green")
    table.add_column("% of Spend", justify="right")
    table.add_column("Avg/Call", justify="right", style="yellow")

    for model, data in sorted(by_model.items(), key=lambda x: x[1]["cost"], reverse=True):
        pct = (data["cost"] / total_cost * 100) if total_cost > 0 else 0
        table.add_row(
            model,
            str(data["calls"]),
            _format_cost(data["cost"]),
            f"{pct:.1f}%",
            _format_cost(data["avg_cost_per_call"]),
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{len(generations)}[/bold]",
        f"[bold green]{_format_cost(total_cost)}[/bold green]",
        "100%",
        "",
    )

    console.print(table)


def report_alert(
    generations: list[dict[str, Any]],
    limit: float,
    timeframe: str = "today",
) -> bool:
    """Check if spend exceeds limit and alert. Returns True if exceeded."""
    total = sum(g["cost"] for g in generations)

    if total > limit:
        console.print(
            Panel(
                f"[bold red]⚠ SPEND ALERT![/bold red]\n\n"
                f"Spend ({timeframe}): [bold red]{_format_cost(total)}[/bold red]\n"
                f"Budget limit: [bold]{_format_cost(limit)}[/bold]\n"
                f"Over by: [bold red]{_format_cost(total - limit)}[/bold red]",
                border_style="red",
                title="Budget Alert",
            )
        )
        return True
    else:
        remaining = limit - total
        console.print(
            Panel(
                f"[bold green]✓ Within budget[/bold green]\n\n"
                f"Spend ({timeframe}): [green]{_format_cost(total)}[/green]\n"
                f"Budget limit: [bold]{_format_cost(limit)}[/bold]\n"
                f"Remaining: [bold green]{_format_cost(remaining)}[/bold green]",
                border_style="green",
                title="Budget Check",
            )
        )
        return False


def report_credit_info(credit_info: dict[str, Any]) -> None:
    """Display credit and rate limit info."""
    if not credit_info:
        return

    table = Table(title="OpenRouter Account", box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Key Name", credit_info.get("key_name", "N/A"))
    table.add_row("Credits Remaining", f"${credit_info.get('credits_remaining', 0):.2f}")
    table.add_row("Credits Used", f"${credit_info.get('credits_used', 0):.2f}")
    table.add_row("Rate Limit", f"{credit_info.get('rate_limit_requests', 'N/A')} req/{credit_info.get('rate_limit_interval', 'N/A')}")
    table.add_row("Status", "[red]Disabled[/red]" if credit_info.get("is_disabled") else "[green]Active[/green]")

    console.print(table)


# ── Trust Dashboard Reports (new) ────────────────────────────────────

def report_trust_dashboard(report: TrustReport) -> None:
    """Display the full AI Trust Dashboard."""
    # Header
    console.print()
    console.rule("[bold blue]🛡️  AI Trust Dashboard[/bold blue]")
    console.print(
        f"[dim]Monthly subscription spend: [/dim][bold]${report.total_monthly_spend:.2f}[/bold]  |  "
        f"[dim]Services tracked: [/dim][bold]{len(report.services)}[/bold]  |  "
        f"[dim]Avg trust score: [/dim][bold {_trust_color(int(report.trust_score_avg))}]{report.trust_score_avg:.1f}/10[/bold {_trust_color(int(report.trust_score_avg))}]"
    )

    if report.at_risk_services:
        console.print()
        at_risk_names = [s.name for s in report.services if s.service_id in report.at_risk_services]
        console.print(
            Panel(
                f"[bold red]⚠ AT RISK:[/bold red] {', '.join(at_risk_names)}",
                border_style="red",
            )
        )

    console.print()

    # Services table
    table = Table(title="Tracked AI Services", box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Status")
    table.add_column("Cost/mo", justify="right")
    table.add_column("Trust", justify="center")
    table.add_column("Incidents (30d)", justify="right")
    table.add_column("Transparency")

    for s in report.services:
        trust_style = _trust_color(s.transparency_score)
        trust_cell = f"[bold {trust_style}]{s.transparency_score}/10[/bold {trust_style}]"

        transparency = "📊 Public" if s.has_public_status_page else "[dim]None[/dim]"

        table.add_row(
            s.name,
            _status_icon(s.is_up, s.status_detail),
            f"${s.subscription_cost:.2f}",
            trust_cell,
            str(s.incidents_30d) if s.incidents_30d else "—",
            transparency,
        )

    console.print(table)
    console.print()

    # Trust breakdown
    if report.services:
        _report_trust_breakdown(report)


def _report_trust_breakdown(report: TrustReport) -> None:
    """Show detailed trust breakdown per service."""
    console.rule("[bold]Trust Signal Breakdown[/bold]")
    console.print()

    for s in report.services:
        trust = s.transparency_score

        # Build trust bar
        bar_filled = "█" * trust
        bar_empty = "░" * (10 - trust)
        bar_color = _trust_color(trust)
        bar = f"[{bar_color}]{bar_filled}[/{bar_color}][dim]{bar_empty}[/dim]"

        console.print(f"  [bold]{s.name}[/bold]  {bar}  [{bar_color}]{trust}/10[/{bar_color}]")

        signals = []
        if s.has_public_status_page:
            signals.append("[green]✓[/green] Public status page")
        else:
            signals.append("[red]✗[/red] No status page")
        if s.is_up:
            signals.append("[green]✓[/green] Currently operational")
        else:
            signals.append(f"[red]✗[/red] {s.status_detail}")
        if s.subscription_cost > 0:
            signals.append(f"[dim]$[/dim]{s.subscription_cost:.0f}/mo")
        if s.incidents_30d:
            signals.append(f"[yellow]⚠[/yellow] {s.incidents_30d} incidents (30d)")

        console.print(f"     {'  |  '.join(signals)}")
        console.print()


def report_service_list(known: list[dict[str, Any]]) -> None:
    """Display list of known services available to track."""
    table = Table(title="Available AI Services to Track", box=box.ROUNDED)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("Category", style="dim")
    table.add_column("Tiers", style="yellow")
    table.add_column("Status Page")
    table.add_column("Tracking", justify="center")

    for s in known:
        tiers = ", ".join(f"{t} (${p})" for t, p in sorted(s["tiers"].items(), key=lambda x: x[1]))
        status_page = "[green]✓[/green]" if s.get("status_url") else "[dim]—[/dim]"
        tracking = "[green]●[/green]" if s["tracked"] else "[dim]○[/dim]"

        table.add_row(
            s["id"],
            s["name"],
            s.get("category", "other"),
            tiers,
            status_page,
            tracking,
        )

    console.print(table)
    console.print()
    console.print("[dim]Use [cyan]spendwatch trust add <id>[/cyan] to start tracking a service[/dim]")


def report_trust_added(service_id: str, name: str) -> None:
    """Report a service was added to tracking."""
    console.print(
        Panel(
            f"[green]✓ Now tracking [bold]{name}[/bold][/green]\n\n"
            f"Run [cyan]spendwatch trust[/cyan] to see your trust dashboard.",
            border_style="green",
            title="Service Added",
        )
    )


def report_trust_removed(service_id: str, name: str) -> None:
    """Report a service was removed from tracking."""
    console.print(
        Panel(
            f"[yellow]Stopped tracking [bold]{name}[/bold][/yellow]",
            border_style="yellow",
            title="Service Removed",
        )
    )
