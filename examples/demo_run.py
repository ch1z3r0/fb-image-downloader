"""Demonstration script showcasing the Facebook Downloader pipeline in action."""

import asyncio
import os
import shutil
from pathlib import Path

from rich.console import Console
from fb_downloader.models import MediaItem, ScrapeResult
from fb_downloader.downloader import MediaDownloader

console = Console()


async def run_demo():
    console.print("\n[bold cyan]🚀 Running Facebook Media Downloader Demonstration...[/bold cyan]\n")

    # Sample test high-resolution public images (from reliable CDN test endpoints)
    sample_images = [
        MediaItem(
            url="https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=1920&q=80",
            suggested_filename="photo_001",
            index=1,
            photo_id="10160163935296772_1",
        ),
        MediaItem(
            url="https://images.unsplash.com/photo-1511497584788-87676104235f?w=1920&q=80",
            suggested_filename="photo_002",
            index=2,
            photo_id="10160163935296772_2",
        ),
        MediaItem(
            url="https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=1920&q=80",
            suggested_filename="photo_003",
            index=3,
            photo_id="10160163935296772_3",
        ),
    ]

    mock_result = ScrapeResult(
        post_id="10160163935296772",
        canonical_url="https://www.facebook.com/NASA/posts/10160163935296772",
        original_url="https://www.facebook.com/share/p/NASA10160163935296772/",
        items=sample_images,
        total_discovered=len(sample_images),
    )

    output_dir = "./downloads/10160163935296772"
    console.print(f"[bold green]✨ Discovered {len(sample_images)} photos from post [cyan]{mock_result.post_id}[/cyan][/bold green]")
    console.print(f"[dim]Output destination:[/dim] {output_dir}\n")

    downloader = MediaDownloader()
    result = await downloader.download_all(
        scrape_result=mock_result,
        output_dir=output_dir,
        concurrency=3,
        show_progress=True,
    )

    console.print("\n[bold green]Download Complete![/bold green]")
    console.print(f"Total downloaded files: [bold cyan]{len(result.successful_items)}[/bold cyan]")
    console.print(f"Total size: [bold cyan]{result.total_bytes / (1024*1024):.2f} MB[/bold cyan]")
    console.print(f"Elapsed time: [bold cyan]{result.elapsed_seconds:.2f}s[/bold cyan]\n")

    for f in Path(output_dir).glob("photo_*.*"):
        console.print(f"  [green]✓[/green] Saved: [bold]{f.name}[/bold] ({f.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    asyncio.run(run_demo())
