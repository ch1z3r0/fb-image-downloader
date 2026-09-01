"""Asynchronous streaming media downloader with Rich progress UI."""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import List, Optional

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .cdn_utils import (
    detect_extension_from_bytes,
    detect_extension_from_url,
    mime_to_extension,
    resolve_image_extension,
)
from .config import DownloaderConfig
from .models import DownloadResult, MediaItem, ScrapeResult

logger = logging.getLogger("fb_downloader.downloader")
console = Console()


class MediaDownloader:
    """Handles concurrent, chunked streaming downloads of Facebook media assets."""

    def __init__(self, config: Optional[DownloaderConfig] = None):
        self.config = config or DownloaderConfig()

    async def download_all(
        self,
        scrape_result: ScrapeResult,
        output_dir: Optional[str] = None,
        concurrency: Optional[int] = None,
        show_progress: bool = True,
    ) -> DownloadResult:
        """Download all discovered media items concurrently with real-time progress bars."""
        start_time = time.time()
        post_id = scrape_result.post_id or "post"

        if output_dir:
            target_dir = Path(output_dir).expanduser().resolve()
        else:
            target_dir = (Path(self.config.default_output_root) / post_id).expanduser().resolve()

        target_dir.mkdir(parents=True, exist_ok=True)
        active_concurrency = concurrency or self.config.default_concurrency
        semaphore = asyncio.Semaphore(active_concurrency)

        successful_items: List[MediaItem] = []
        failed_items: List[MediaItem] = []
        total_bytes = 0

        items_to_download = scrape_result.items
        if not items_to_download:
            return DownloadResult(
                post_id=post_id,
                output_dir=str(target_dir),
                successful_items=[],
                failed_items=[],
                total_bytes=0,
                elapsed_seconds=0.0,
            )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Referer": "https://www.facebook.com/",
        }

        async with httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(self.config.timeout_seconds),
            follow_redirects=True,
            limits=httpx.Limits(max_connections=active_concurrency * 2),
        ) as client:
            if show_progress:
                progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[bold cyan]{task.fields[filename]}"),
                    BarColumn(bar_width=30),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    DownloadColumn(),
                    TransferSpeedColumn(),
                    TimeRemainingColumn(),
                    console=console,
                )

                with progress:
                    overall_task = progress.add_task(
                        "Overall Progress",
                        total=len(items_to_download),
                        filename="[bold green]Total Files[/bold green]",
                    )

                    async def worker(item: MediaItem, index: int):
                        async with semaphore:
                            item_task = progress.add_task(
                                "Downloading",
                                total=None,
                                filename=f"photo_{index:03d}",
                            )
                            res_item = await self._download_single(
                                client=client,
                                item=item,
                                index=index,
                                target_dir=target_dir,
                                progress=progress,
                                task_id=item_task,
                            )
                            progress.advance(overall_task)
                            progress.remove_task(item_task)
                            return res_item

                    tasks = [
                        worker(item, idx)
                        for idx, item in enumerate(items_to_download, start=1)
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)

            else:
                async def worker_headless(item: MediaItem, index: int):
                    async with semaphore:
                        return await self._download_single(
                            client=client,
                            item=item,
                            index=index,
                            target_dir=target_dir,
                        )

                tasks = [
                    worker_headless(item, idx)
                    for idx, item in enumerate(items_to_download, start=1)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                logger.error(f"Download task exception: {res}")
            elif isinstance(res, MediaItem) and res.local_path:
                successful_items.append(res)
                total_bytes += res.file_size_bytes or 0
            elif isinstance(res, MediaItem):
                failed_items.append(res)

        elapsed = time.time() - start_time
        return DownloadResult(
            post_id=post_id,
            output_dir=str(target_dir.resolve()),
            successful_items=successful_items,
            failed_items=failed_items,
            total_bytes=total_bytes,
            elapsed_seconds=elapsed,
        )

    async def _download_single(
        self,
        client: httpx.AsyncClient,
        item: MediaItem,
        index: int,
        target_dir: Path,
        progress: Optional[Progress] = None,
        task_id=None,
    ) -> MediaItem:
        """Stream a single media item in chunks, format extension, and write to disk."""
        target_dir.mkdir(parents=True, exist_ok=True)
        url = item.url
        base_name = item.suggested_filename or f"photo_{index:03d}"
        temp_file_path = target_dir / f".tmp_{base_name}_{int(time.time()*1000)}"

        for attempt in range(1, self.config.max_retries + 1):
            try:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        logger.warning(
                            f"HTTP {response.status_code} fetching {url} (attempt {attempt})"
                        )
                        if attempt == self.config.max_retries:
                            return item
                        await asyncio.sleep(0.5 * attempt)
                        continue

                    content_type = response.headers.get("content-type", "image/jpeg")
                    total_size = response.headers.get("content-length")
                    total_size_int = int(total_size) if total_size and total_size.isdigit() else None

                    if progress and task_id is not None and total_size_int:
                        progress.update(task_id, total=total_size_int)

                    extension = resolve_image_extension(url=url, content_type=content_type)
                    downloaded_bytes = 0
                    first_chunk = True

                    with open(temp_file_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=self.config.chunk_size):
                            if first_chunk:
                                # Inspect leading binary magic bytes for exact extension ground truth
                                exact_ext = resolve_image_extension(
                                    url=url,
                                    content_type=content_type,
                                    magic_bytes=chunk[:64],
                                )
                                if exact_ext:
                                    extension = exact_ext
                                first_chunk = False

                            f.write(chunk)
                            downloaded_bytes += len(chunk)
                            if progress and task_id is not None:
                                progress.update(task_id, completed=downloaded_bytes)

                    # Finalize filename with correct extension
                    final_filename = f"{base_name}{extension}"
                    final_file_path = target_dir / final_filename

                    # Rename temp file to final destination
                    if temp_file_path.exists():
                        if final_file_path.exists():
                            final_file_path.unlink()
                        temp_file_path.rename(final_file_path)

                    item.mime_type = content_type
                    item.suggested_filename = final_filename
                    item.local_path = str(final_file_path.resolve())
                    item.file_size_bytes = downloaded_bytes
                    return item

            except (httpx.HTTPError, OSError) as e:
                logger.warning(f"Error downloading {url} (attempt {attempt}): {e}")
                if temp_file_path.exists():
                    try:
                        temp_file_path.unlink()
                    except Exception:
                        pass
                if attempt == self.config.max_retries:
                    return item
                await asyncio.sleep(0.5 * attempt)

        return item
