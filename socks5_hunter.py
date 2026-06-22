"""
socks5_hunter.py
═══════════════════════════════════════════════════════════════════════════
SOCKS5 Proxy Hunter — combined power of ProxyBroker + iloveproxies.

Phase 1 → Download from 10 curated GitHub raw lists
Phase 2 → Scrape 8 web providers (adapted from ProxyBroker)
Phase 3 → Validate all collected proxies through SOCKS5
Phase 4 → Save working proxies + print summary

Usage:
    python socks5_hunter.py
    python socks5_hunter.py --concurrency 200 --timeout 10
═══════════════════════════════════════════════════════════════════════════
"""

import argparse
import asyncio
import os
import sys
import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text
from rich import box

from sources.github_lists import fetch_all as github_fetch
from sources.web_scraper import scrape_all as web_scrape
from validator import validate_batch, ProxyResult

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "working_socks5.txt")

console = Console()


# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
BANNER = r"""
[bold cyan]
 ███████╗ ██████╗  ██████╗██╗  ██╗███████╗███████╗
 ██╔════╝██╔═══██╗██╔════╝██║ ██╔╝██╔════╝██╔════╝
 ███████╗██║   ██║██║     █████╔╝ ███████╗███████╗
 ╚════██║██║   ██║██║     ██╔═██╗ ╚════██║╚════██║
 ███████║╚██████╔╝╚██████╗██║  ██╗███████║███████║
 ╚══════╝ ╚═════╝  ╚═════╝╚═╝  ╚═╝╚══════╝╚══════╝
[/bold cyan]
[bold white]         ⚡ SOCKS5 PROXY HUNTER ⚡[/bold white]
[dim]   ProxyBroker × iloveproxies — Combined Engine[/dim]
"""


def print_banner():
    console.print(BANNER)


# ---------------------------------------------------------------------------
# Phase 1 — GitHub Lists
# ---------------------------------------------------------------------------
async def phase_github(progress, task_id) -> set[str]:
    async def cb(count):
        progress.advance(task_id, 1)

    proxies = await github_fetch(progress_callback=cb)
    # Ensure the bar fills to 10 (total sources)
    progress.update(task_id, completed=10)
    return proxies


# ---------------------------------------------------------------------------
# Phase 2 — Web Scraping
# ---------------------------------------------------------------------------
async def phase_scrape(progress, task_id) -> set[str]:
    async def cb(count):
        progress.advance(task_id, 1)

    proxies = await web_scrape(progress_callback=cb)
    progress.update(task_id, completed=8)
    return proxies


# ---------------------------------------------------------------------------
# Phase 3 — Validation with live table
# ---------------------------------------------------------------------------
async def phase_validate(
    proxies: set[str],
    concurrency: int,
    console: Console,
) -> list[ProxyResult]:
    working: list[ProxyResult] = []
    tested = 0
    total = len(proxies)
    start_time = time.perf_counter()

    def make_layout():
        # Stats panel
        elapsed = time.perf_counter() - start_time
        rate = tested / elapsed if elapsed > 0 else 0
        pct = (tested / total * 100) if total > 0 else 0

        stats_text = Text()
        stats_text.append(f"  Tested: ", style="bold white")
        stats_text.append(f"{tested:,}", style="bold yellow")
        stats_text.append(f" / {total:,}\n", style="dim")
        stats_text.append(f"  Alive:  ", style="bold white")
        stats_text.append(f"{len(working):,}", style="bold green")
        stats_text.append(f"  ({pct:.1f}% done)\n", style="dim")
        stats_text.append(f"  Speed:  ", style="bold white")
        stats_text.append(f"{rate:.0f}", style="bold cyan")
        stats_text.append(f" proxies/sec\n", style="dim")
        stats_text.append(f"  Time:   ", style="bold white")
        stats_text.append(f"{elapsed:.0f}s", style="bold magenta")

        stats_panel = Panel(
            stats_text,
            title="[bold white]⚡ Validation Progress[/bold white]",
            border_style="cyan",
            box=box.DOUBLE_EDGE,
            padding=(0, 1),
        )

        # Live proxy table — last 15 found
        table = Table(
            title="[bold green]🟢 Working SOCKS5 Proxies[/bold green]",
            box=box.ROUNDED,
            border_style="green",
            show_lines=False,
            padding=(0, 1),
        )
        table.add_column("#", style="dim", width=5, justify="right")
        table.add_column("Proxy", style="bold white", min_width=22)
        table.add_column("Latency", style="cyan", justify="right", width=10)
        table.add_column("Status", justify="center", width=8)

        display_proxies = working[-15:]  # last 15
        for i, p in enumerate(display_proxies, start=max(1, len(working) - 14)):
            latency_style = "green" if p.latency_ms < 2000 else "yellow" if p.latency_ms < 5000 else "red"
            table.add_row(
                str(i),
                p.proxy,
                f"[{latency_style}]{p.latency_ms:.0f}ms[/{latency_style}]",
                "[bold green]✓ LIVE[/bold green]",
            )

        # Progress bar
        bar_filled = int(pct / 2)
        bar_empty = 50 - bar_filled
        bar = f"[cyan]{'█' * bar_filled}[/cyan][dim]{'░' * bar_empty}[/dim] {pct:.1f}%"

        from rich.columns import Columns
        from rich.padding import Padding

        return Padding(
            Text.from_markup(f"\n{bar}\n\n"),
            (0, 2),
        ), stats_panel, table

    async def on_result(result: ProxyResult):
        nonlocal tested
        tested += 1
        if result.alive:
            working.append(result)

    # Start validation with live display
    with Live(console=console, refresh_per_second=4, transient=True) as live:
        # Launch validation as a background task
        val_task = asyncio.ensure_future(
            validate_batch(proxies, concurrency=concurrency, on_result=on_result)
        )

        while not val_task.done():
            bar, stats, table = make_layout()
            from rich.console import Group
            live.update(Group(bar, stats, table))
            await asyncio.sleep(0.25)

        # Final update
        bar, stats, table = make_layout()
        from rich.console import Group
        live.update(Group(bar, stats, table))

        await val_task  # propagate exceptions

    return working


# ---------------------------------------------------------------------------
# Save results
# ---------------------------------------------------------------------------
def save_results(working: list[ProxyResult]):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Sort by latency (fastest first)
    working.sort(key=lambda p: p.latency_ms)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for p in working:
            f.write(f"{p.proxy}\n")

    return OUTPUT_FILE


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
def print_summary(total_collected: int, results: list[ProxyResult], elapsed: float, filepath: str):
    working = [r for r in results if r.alive]

    console.print()

    summary = Table(
        title="[bold white]📊 HUNT SUMMARY[/bold white]",
        box=box.DOUBLE_EDGE,
        border_style="cyan",
        show_lines=True,
        padding=(0, 2),
    )
    summary.add_column("Metric", style="bold white", width=24)
    summary.add_column("Value", style="bold", justify="right", width=20)

    summary.add_row("Total Collected", f"[yellow]{total_collected:,}[/yellow]")
    summary.add_row("Tested", f"[yellow]{len(results):,}[/yellow]")
    summary.add_row("Alive SOCKS5", f"[bold green]{len(working):,}[/bold green]")
    summary.add_row(
        "Success Rate",
        f"[cyan]{len(working)/max(len(results),1)*100:.1f}%[/cyan]",
    )

    if working:
        avg_latency = sum(p.latency_ms for p in working) / len(working)
        fastest = min(working, key=lambda p: p.latency_ms)
        summary.add_row("Avg Latency", f"[cyan]{avg_latency:.0f}ms[/cyan]")
        summary.add_row(
            "Fastest Proxy",
            f"[green]{fastest.proxy} ({fastest.latency_ms:.0f}ms)[/green]",
        )

    summary.add_row("Total Time", f"[magenta]{elapsed:.1f}s[/magenta]")
    summary.add_row("Saved To", f"[dim]{filepath}[/dim]")

    console.print(summary)
    console.print()

    if working:
        # Top 5 fastest
        console.print(
            Panel(
                "\n".join(
                    f"  [bold green]{i}.[/bold green] {p.proxy}  [cyan]({p.latency_ms:.0f}ms)[/cyan]"
                    for i, p in enumerate(working[:5], 1)
                ),
                title="[bold white]🏆 Top 5 Fastest Proxies[/bold white]",
                border_style="green",
                box=box.ROUNDED,
            )
        )
    else:
        console.print(
            "[bold red]No working SOCKS5 proxies found. "
            "Try increasing timeout or concurrency.[/bold red]"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(concurrency: int = 150):
    print_banner()
    t0 = time.perf_counter()

    # ── Phase 1 + 2: Collect ──────────────────────────────────────────────
    console.print(
        Panel(
            "[bold white]Phase 1/3 — Collecting proxies from all sources…[/bold white]",
            border_style="cyan",
            box=box.ROUNDED,
        )
    )

    progress = Progress(
        SpinnerColumn("dots"),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(bar_width=40, complete_style="cyan", finished_style="green"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        gh_task = progress.add_task("GitHub Lists", total=10)
        ws_task = progress.add_task("Web Scrapers", total=8)

        github_proxies, web_proxies = await asyncio.gather(
            phase_github(progress, gh_task),
            phase_scrape(progress, ws_task),
        )

    all_proxies = github_proxies | web_proxies

    console.print(
        f"\n  [bold green]✓[/bold green] GitHub lists:  [bold yellow]{len(github_proxies):,}[/bold yellow] proxies"
    )
    console.print(
        f"  [bold green]✓[/bold green] Web scrapers:  [bold yellow]{len(web_proxies):,}[/bold yellow] proxies"
    )
    console.print(
        f"  [bold green]✓[/bold green] Combined:      [bold white]{len(all_proxies):,}[/bold white] unique proxies\n"
    )

    if not all_proxies:
        console.print("[bold red]No proxies collected! Check your internet connection.[/bold red]")
        return

    # ── Phase 3: Validate ─────────────────────────────────────────────────
    console.print(
        Panel(
            f"[bold white]Phase 2/3 — Validating {len(all_proxies):,} proxies "
            f"(concurrency: {concurrency})…[/bold white]",
            border_style="yellow",
            box=box.ROUNDED,
        )
    )

    working = await phase_validate(all_proxies, concurrency, console)

    # ── Phase 4: Save + Summary ───────────────────────────────────────────
    console.print(
        Panel(
            "[bold white]Phase 3/3 — Saving results…[/bold white]",
            border_style="green",
            box=box.ROUNDED,
        )
    )

    filepath = save_results(working)
    elapsed = time.perf_counter() - t0

    # Build a full results list for summary (we only have working proxies
    # since dead ones are not stored, but we know the total)
    print_summary(len(all_proxies), working, elapsed, filepath)


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------
def cli():
    parser = argparse.ArgumentParser(
        description="SOCKS5 Proxy Hunter — scrape, collect & validate SOCKS5 proxies",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-c", "--concurrency",
        type=int,
        default=150,
        help="Max concurrent validation connections (default: 150)",
    )
    args = parser.parse_args()

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main(concurrency=args.concurrency))


if __name__ == "__main__":
    cli()
