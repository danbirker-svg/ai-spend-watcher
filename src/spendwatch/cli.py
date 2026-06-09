"""CLI entry point for AI Spend Watcher."""

import sys
from datetime import date, timedelta

import click
from rich.console import Console

from . import __version__
from .config import load_config, ensure_config_dir
from .api import get_daily_spend, get_total_spend, fetch_credit_info
from .reporter import (
    report_daily,
    report_total,
    report_models,
    report_alert,
    report_credit_info,
)
from .cache import clear_cache, cache_stats

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


if __name__ == "__main__":
    main()
