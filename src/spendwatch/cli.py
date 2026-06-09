"""CLI entry point for AI Spend Watcher."""

import sys
from datetime import date, timedelta

import click
from rich.console import Console
from rich.table import Table
from rich import box

from . import __version__
from .config import load_config, ensure_config_dir
from .api import get_daily_spend, get_total_spend, fetch_credit_info
from .reporter import (
    report_daily,
    report_total,
    report_models,
    report_alert,
    report_credit_info,
    report_trust_dashboard,
    report_service_list,
    report_trust_added,
    report_trust_removed,
)
from .cache import clear_cache, cache_stats
from .trust import (
    check_all_services,
    add_service,
    remove_service,
    log_incident,
    list_known_services,
    load_services,
)

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="spendwatch")
@click.pass_context
def main(ctx: click.Context) -> None:
    """AI Spend Watcher — Track your AI API spending across providers.

    Monitors costs from OpenRouter and other AI API providers.
    Configure via ~/.spendwatch/config.toml or OPENROUTER_API_KEY env var.
    """
    ctx.ensure_object(dict)
    config = load_config()
    ctx.obj["config"] = config


@main.command()
@click.option("--date", "-d", "date_str", default=None, help="Date to check (YYYY-MM-DD), defaults to today")
@click.option("--no-cache", is_flag=True, help="Skip cache, fetch fresh data")
@click.pass_context
def daily(ctx: click.Context, date_str: str | None, no_cache: bool) -> None:
    """Show today's spend by model."""
    config = ctx.obj["config"]

    if not config.has_api_key:
        console.print("[red]No API key configured.[/red] Set OPENROUTER_API_KEY or add to ~/.spendwatch/config.toml")
        sys.exit(1)

    target = date_str or date.today().isoformat()

    with console.status(f"[bold green]Fetching spend data for {target}..."):
        generations = get_daily_spend(config, target, use_cache=not no_cache)

    report_daily(generations, target)


@main.command()
@click.option("--from", "-f", "from_date", default=None, help="Start date (YYYY-MM-DD), defaults to 30 days ago")
@click.option("--to", "-t", "to_date", default=None, help="End date (YYYY-MM-DD), defaults to today")
@click.pass_context
def total(ctx: click.Context, from_date: str | None, to_date: str | None) -> None:
    """Show total spend across a timeframe."""
    config = ctx.obj["config"]

    if not config.has_api_key:
        console.print("[red]No API key configured.[/red] Set OPENROUTER_API_KEY or add to ~/.spendwatch/config.toml")
        sys.exit(1)

    fd = from_date or (date.today() - timedelta(days=30)).isoformat()
    td = to_date or date.today().isoformat()

    with console.status(f"[bold green]Fetching spend data from {fd} to {td}..."):
        generations = get_total_spend(config, from_date=fd, to_date=td)

    report_total(generations, fd, td)


@main.command()
@click.option("--limit", "-l", type=float, required=True, help="Spend limit in USD (e.g. 5.00)")
@click.option("--date", "-d", "date_str", default=None, help="Date to check (YYYY-MM-DD), defaults to today")
@click.pass_context
def alert(ctx: click.Context, limit: float, date_str: str | None) -> None:
    """Alert if spend exceeds a specified limit."""
    config = ctx.obj["config"]

    if not config.has_api_key:
        console.print("[red]No API key configured.[/red] Set OPENROUTER_API_KEY or add to ~/.spendwatch/config.toml")
        sys.exit(1)

    target = date_str or date.today().isoformat()

    with console.status(f"[bold green]Checking spend for {target}..."):
        generations = get_daily_spend(config, target, use_cache=True)

    exceeded = report_alert(generations, limit, timeframe=target)
    if exceeded:
        sys.exit(1)


@main.command()
@click.option("--from", "-f", "from_date", default=None, help="Start date (YYYY-MM-DD), defaults to 30 days ago")
@click.option("--to", "-t", "to_date", default=None, help="End date (YYYY-MM-DD), defaults to today")
@click.pass_context
def models(ctx: click.Context, from_date: str | None, to_date: str | None) -> None:
    """Show cost breakdown by model."""
    config = ctx.obj["config"]

    if not config.has_api_key:
        console.print("[red]No API key configured.[/red] Set OPENROUTER_API_KEY or add to ~/.spendwatch/config.toml")
        sys.exit(1)

    fd = from_date or (date.today() - timedelta(days=30)).isoformat()
    td = to_date or date.today().isoformat()

    with console.status(f"[bold green]Fetching model data from {fd} to {td}..."):
        generations = get_total_spend(config, from_date=fd, to_date=td)

    report_models(generations)


@main.command()
@click.pass_context
def account(ctx: click.Context) -> None:
    """Show OpenRouter account info (credits, rate limits)."""
    config = ctx.obj["config"]

    if not config.has_api_key:
        console.print("[red]No API key configured.[/red] Set OPENROUTER_API_KEY or add to ~/.spendwatch/config.toml")
        sys.exit(1)

    with console.status("[bold green]Fetching account info..."):
        info = fetch_credit_info(config)

    if info:
        report_credit_info(info)
    else:
        console.print("[yellow]Could not fetch account info. Check your API key.[/yellow]")


@main.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize config directory and default config file."""
    config_dir = ensure_config_dir()
    console.print(f"[green]✓[/green] Config directory created: {config_dir}")
    console.print(f"[green]✓[/green] Default config written: {config_dir / 'config.toml'}")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print("  1. Edit [cyan]~/.spendwatch/config.toml[/cyan] and add your OpenRouter API key")
    console.print("     OR set the [cyan]OPENROUTER_API_KEY[/cyan] environment variable")
    console.print("  2. Run [cyan]spendwatch daily[/cyan] to see today's spend")


@main.command()
@click.option("--clear", is_flag=True, help="Clear all cached data")
@click.pass_context
def cache(ctx: click.Context, clear: bool) -> None:
    """Show or clear cache."""
    if clear:
        count = clear_cache()
        console.print(f"[green]✓[/green] Cleared {count} cached files")
    else:
        stats = cache_stats()
        console.print(f"Cache directory: [cyan]{stats['cache_dir']}[/cyan]")
        console.print(f"Cached files: [bold]{stats['files']}[/bold]")
        console.print(f"Total size: [bold]{stats['total_size_human']}[/bold]")


# ── Trust Dashboard commands ────────────────────────────────────────

@main.group()
def trust() -> None:
    """AI Trust Dashboard — monitor service health, reliability, and billing fairness.

    Track paid AI services (ChatGPT, Claude, Manus, etc.) for outages,
    billing issues, and transparency. Don't just track spend — track trust.
    """
    pass


@trust.command(name="check")
@click.pass_context
def trust_check(ctx: click.Context) -> None:
    """Run a full trust check on all tracked services.

    Checks status pages, counts recent incidents, and calculates
    a trust score (1-10) for each service based on transparency,
    reliability, and billing fairness.
    """
    console.print("[bold blue]🛡️  Running AI Trust check...[/bold blue]")
    console.print()

    with console.status("[bold green]Checking service status pages..."):
        report = check_all_services()

    report_trust_dashboard(report)


@trust.command(name="add")
@click.argument("service_id")
@click.option("--tier", "-t", default="pro", help="Subscription tier (e.g. pro, plus, starter)")
@click.pass_context
def trust_add(ctx: click.Context, service_id: str, tier: str) -> None:
    """Add an AI service to your trust tracking.

    SERVICE_ID is the service slug (e.g. chatgpt, claude, manus, cursor, perplexity).
    Use 'spendwatch trust list' to see all known services.
    """
    known = {s["id"]: s for s in list_known_services()}

    if service_id not in known:
        console.print(f"[red]Unknown service: {service_id}[/red]")
        console.print(f"Known services: {', '.join(known)}")
        return

    added = add_service(service_id, tier)
    if added:
        report_trust_added(service_id, known[service_id]["name"])
    else:
        console.print(f"[yellow]Already tracking {service_id}[/yellow]")


@trust.command(name="remove")
@click.argument("service_id")
@click.pass_context
def trust_remove(ctx: click.Context, service_id: str) -> None:
    """Stop tracking a service."""
    known = {s["id"]: s for s in list_known_services()}
    name = known.get(service_id, {}).get("name", service_id)

    removed = remove_service(service_id)
    if removed:
        report_trust_removed(service_id, name)
    else:
        console.print(f"[yellow]{service_id} is not being tracked[/yellow]")


@trust.command(name="list")
@click.pass_context
def trust_list(ctx: click.Context) -> None:
    """List all known AI services available to track."""
    known = list_known_services()
    report_service_list(known)


@trust.command(name="incident")
@click.argument("service_id")
@click.argument("description")
@click.pass_context
def trust_incident(ctx: click.Context, service_id: str, description: str) -> None:
    """Log an incident for a tracked service.

    Example: spendwatch trust incident manus "Charged $400 but agent execution failed silently"
    """
    log_incident(service_id, description)
    console.print(f"[green]✓[/green] Incident logged for [bold]{service_id}[/bold]")
    console.print(f"   [dim]{description}[/dim]")


@trust.command(name="costs")
@click.pass_context
def trust_costs(ctx: click.Context) -> None:
    """Show your total monthly AI subscription spend across all tracked services."""
    services = load_services()
    if not services:
        console.print("[yellow]No services tracked yet.[/yellow] Run [cyan]spendwatch trust add <service>[/cyan]")
        return

    total = sum(s.get("monthly_cost", 0) for s in services.values())

    table = Table(title="Monthly AI Subscription Costs", box=box.ROUNDED)
    table.add_column("Service", style="cyan")
    table.add_column("Tier", style="dim")
    table.add_column("Cost/mo", justify="right", style="green")

    from .trust import KNOWN_SERVICES

    for sid, cfg in sorted(services.items()):
        info = KNOWN_SERVICES.get(sid, {})
        table.add_row(
            info.get("name", sid),
            cfg.get("subscription", "?"),
            f"${cfg['monthly_cost']:.2f}",
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]",
        "",
        f"[bold green]${total:.2f}[/bold green]",
    )

    console.print(table)
    console.print()
    console.print(f"[dim]Plus API costs (tracked via spendwatch daily/total)[/dim]")


if __name__ == "__main__":
    main()
