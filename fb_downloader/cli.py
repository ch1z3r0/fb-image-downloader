"""Typer CLI interface for Facebook Post Image Downloader."""

import asyncio
import logging
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Optional

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .downloader import MediaDownloader
from .models import ScrapeResult
from .scraper import FacebookScraper
from .url_utils import is_valid_facebook_url
from .validator import install_playwright_browsers, validate_environment

app = typer.Typer(
    name="fb-downloader",
    help="🚀 Production-grade Facebook Post Image Downloader CLI.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Configure structured logging level and formatting."""
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command(name="download")
def main(
    url: Optional[str] = typer.Argument(
        None,
        help="Facebook post URL (e.g., https://www.facebook.com/... or https://fb.com/share/p/...)",
    ),
    output: Optional[str] = typer.Option(
        None,
        "--output",
        "-o",
        help="Custom output directory path (default: ./downloads/<post_id>/)",
    ),
    headless: bool = typer.Option(
        True,
        "--headless/--no-headless",
        help="Run Playwright Chromium browser in headless mode.",
    ),
    concurrency: int = typer.Option(
        5,
        "--concurrency",
        "-c",
        help="Maximum concurrent image downloads.",
        min=1,
        max=20,
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable detailed debug logs.",
    ),
    check_env: bool = typer.Option(
        True,
        "--check-env/--no-check-env",
        help="Perform automated pre-flight environment checks.",
    ),
    install_browsers: bool = typer.Option(
        False,
        "--install-browsers",
        help="Install required Playwright Chromium browser binaries and exit.",
    ),
    check_only: bool = typer.Option(
        False,
        "--check-only",
        help="Run environment health check without scraping.",
    ),
    ui: bool = typer.Option(
        False,
        "--ui",
        help="Launch the interactive Web UI dashboard.",
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to run Web UI on (default: 8000).",
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="Host interface for Web UI (default: 0.0.0.0 for Local Network access).",
    ),
    ssl: bool = typer.Option(
        False,
        "--ssl",
        help="Enable HTTPS with local self-signed certificate to unlock client folder picking on LAN.",
    ),
):
    """Scrape and download all high-resolution images attached to a Facebook post."""
    setup_logging(verbose)

    # 1. Standalone flags
    if install_browsers:
        console.print("[bold blue]Installing Playwright Chromium browser binaries...[/bold blue]")
        if install_playwright_browsers():
            console.print("[bold green]✅ Chromium installed successfully![/bold green]")
            raise typer.Exit(code=0)
        else:
            console.print("[bold red]❌ Installation failed.[/bold red]")
            raise typer.Exit(code=1)

    if check_only:
        is_valid, msg = validate_environment(output or "./downloads")
        if is_valid:
            console.print(f"[bold green]✅ {msg}[/bold green]")
            raise typer.Exit(code=0)
        else:
            console.print(f"[bold red]❌ {msg}[/bold red]")
            raise typer.Exit(code=1)

    # 2. Launch UI Web Server if requested or if 'ui' is the first arg
    if ui or (url and url.lower() == "ui"):
        _start_ui_server(host=host, port=port, ssl_enabled=ssl)
        return

    # If no URL was provided
    if not url:
        console.print("[bold red]❌ Error: Missing Facebook post URL argument.[/bold red]")
        console.print("Usage: python main.py <url> --output <dir> --headless")
        console.print("Or launch Web UI with: [bold cyan]python main.py --ui[/bold cyan]")
        raise typer.Exit(code=1)

    # 3. URL format validation
    if not is_valid_facebook_url(url):
        console.print(
            f"[bold red]❌ Error:[/bold red] '{url}' is not recognized as a valid Facebook URL.\n"
            "Supported formats: https://facebook.com/.../posts/..., https://fb.com/share/p/..., etc.",
            style="red",
        )
        raise typer.Exit(code=1)

    # 4. Automated environment validation
    if check_env:
        is_valid, msg = validate_environment(output or "./downloads")
        if not is_valid:
            console.print(f"[bold yellow]⚠️ Environment Check Failed:[/bold yellow] {msg}")
            if "playwright install" in msg.lower():
                install_choice = typer.confirm(
                    "Would you like to install the required Playwright Chromium browser now?"
                )
                if install_choice:
                    if install_playwright_browsers():
                        console.print("[bold green]✅ Chromium installed successfully![/bold green]")
                    else:
                        console.print("[bold red]❌ Installation failed. Please run: playwright install chromium[/bold red]")
                        raise typer.Exit(code=1)
                else:
                    raise typer.Exit(code=1)
            else:
                raise typer.Exit(code=1)

    console.print(
        Panel.fit(
            f"[bold cyan]Facebook Post Image Downloader[/bold cyan]\n"
            f"[dim]URL:[/dim] {url}\n"
            f"[dim]Headless:[/dim] {headless} | [dim]Concurrency:[/dim] {concurrency}",
            border_style="cyan",
        )
    )

    # 5. Run Async Scraper & Downloader pipeline
    try:
        asyncio.run(
            _run_pipeline(
                url=url,
                output_dir=output,
                headless=headless,
                concurrency=concurrency,
            )
        )
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Process interrupted by user.[/bold yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]❌ Fatal Error:[/bold red] {e}", style="red")
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)


def _ensure_ssl_cert():
    """Generate or retrieve a local self-signed certificate for HTTPS on LAN."""
    ssl_dir = Path.home() / ".fb_downloader_ssl"
    ssl_dir.mkdir(parents=True, exist_ok=True)
    key_file = ssl_dir / "key.pem"
    cert_file = ssl_dir / "cert.pem"
    if not (key_file.exists() and cert_file.exists()):
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048",
                "-keyout", str(key_file), "-out", str(cert_file),
                "-days", "365", "-nodes",
                "-subj", "/CN=localhost",
            ],
            check=True,
            capture_output=True,
        )
    return str(key_file), str(cert_file)


def _start_ui_server(host: str = "0.0.0.0", port: int = 8000, ssl_enabled: bool = False) -> None:
    """Start FastAPI Uvicorn web server and open browser."""
    from .validator import get_local_ip

    ssl_keyfile, ssl_certfile = None, None
    protocol = "http"

    if ssl_enabled:
        try:
            ssl_keyfile, ssl_certfile = _ensure_ssl_cert()
            protocol = "https"
            console.print("[bold green]🔒 SSL certificate ready — starting HTTPS server.[/bold green]")
        except Exception as e:
            console.print(f"[bold yellow]⚠️ Could not generate SSL certificate ({e}). Running on HTTP.[/bold yellow]")

    local_ip = get_local_ip()
    local_url = f"{protocol}://localhost:{port}"
    network_url = f"{protocol}://{local_ip}:{port}"

    ssl_note = " (HTTPS — Folder Picker enabled on LAN)" if protocol == "https" else ""
    console.print(
        Panel.fit(
            f"[bold green]🚀 Facebook Downloader PRO - Local Network Server{ssl_note}[/bold green]\n\n"
            f"  [bold cyan]🏠 Local Host:[/bold cyan]    [underline]{local_url}[/underline]\n"
            f"  [bold magenta]📱 Local Network:[/bold magenta] [underline]{network_url}[/underline] [dim](Open on phone / other PCs on same Wi-Fi)[/dim]\n\n"
            f"[dim]Press Ctrl+C to stop the server[/dim]",
            border_style="green",
        )
    )
    try:
        webbrowser.open(local_url)
    except Exception:
        pass

    if ssl_keyfile and ssl_certfile:
        uvicorn.run(
            "fb_downloader.web_server:app",
            host=host, port=port, log_level="info",
            ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile,
        )
    else:
        uvicorn.run("fb_downloader.web_server:app", host=host, port=port, log_level="info")


async def _run_pipeline(
    url: str,
    output_dir: Optional[str],
    headless: bool,
    concurrency: int,
) -> None:
    """Execute asynchronous scraping followed by concurrent streaming download."""
    # Step 1: Scrape media
    with console.status("[bold green]Resolving post & extracting media sources with Playwright...[/bold green]"):
        scraper = FacebookScraper(headless=headless)
        async with scraper:
            scrape_result: ScrapeResult = await scraper.scrape_post(url)

    if not scrape_result.items:
        console.print("[bold yellow]⚠️ No high-resolution images found in this Facebook post.[/bold yellow]")
        return

    console.print(
        f"[bold green]✨ Found {len(scrape_result.items)} high-res image(s) for Post ID: [cyan]{scrape_result.post_id}[/cyan][/bold green]"
    )

    # Step 2: Download media
    downloader = MediaDownloader()
    download_result = await downloader.download_all(
        scrape_result=scrape_result,
        output_dir=output_dir,
        concurrency=concurrency,
        show_progress=True,
    )

    # Step 3: Print summary report table
    table = Table(title="Download Summary", header_style="bold magenta")
    table.add_column("#", justify="right", style="cyan", no_wrap=True)
    table.add_column("Filename", style="green")
    table.add_column("Size", justify="right", style="blue")
    table.add_column("Status", justify="center", style="bold")

    for item in download_result.successful_items:
        size_kb = f"{(item.file_size_bytes or 0) / 1024:.1f} KB"
        table.add_row(
            str(item.index),
            item.suggested_filename or "image.jpg",
            size_kb,
            "[green]Downloaded[/green]",
        )

    for item in download_result.failed_items:
        table.add_row(
            str(item.index),
            item.suggested_filename or "image.jpg",
            "-",
            "[red]Failed[/red]",
        )

    console.print(table)

    mb_downloaded = download_result.total_bytes / (1024 * 1024)
    console.print(
        f"\n[bold green]🎉 Done![/bold green] Downloaded [bold]{len(download_result.successful_items)}[/bold] file(s) "
        f"({mb_downloaded:.2f} MB) in {download_result.elapsed_seconds:.2f}s."
    )
    console.print(f"[bold cyan]📁 Output Directory:[/bold cyan] {download_result.output_dir}\n")
