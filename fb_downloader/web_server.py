"""FastAPI Web Server for Facebook Post Image Downloader UI."""

import asyncio
import io
import logging
import os
import platform
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .cdn_utils import (
    detect_extension_from_bytes,
    detect_extension_from_url,
    mime_to_extension,
    resolve_image_extension,
)
from .config import ScraperConfig
from .downloader import MediaDownloader
from .models import DownloadResult, MediaItem, ScrapeResult
from .scraper import FacebookScraper
from .url_utils import is_valid_facebook_url
from .validator import get_local_ip, validate_environment

logger = logging.getLogger("fb_downloader.web")

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

app = FastAPI(
    title="Facebook Post Image Downloader UI",
    description="Modern Web Interface for Facebook Media Extraction and Download",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeRequest(BaseModel):
    url: str
    headless: bool = True


class DownloadRequest(BaseModel):
    post_id: str
    items: List[MediaItem]
    output_dir: Optional[str] = None
    concurrency: int = 5


class OpenFolderRequest(BaseModel):
    path: str


class ZipDownloadRequest(BaseModel):
    post_id: str
    items: List[MediaItem]
    folder_name: Optional[str] = None


@app.get("/api/health")
async def health_check():
    """Check environment health, Playwright readiness, and system details."""
    from .validator import get_local_ip

    is_valid, msg = validate_environment()
    local_ip = get_local_ip()
    return {
        "status": "healthy" if is_valid else "warning",
        "message": msg,
        "os": platform.system(),
        "python_version": platform.python_version(),
        "local_ip": local_ip,
        "network_url": f"http://{local_ip}:8000",
    }


@app.post("/api/scrape", response_model=ScrapeResult)
async def api_scrape_post(req: ScrapeRequest):
    """Scrape media items from the provided Facebook URL."""
    url = req.url.strip()
    if not is_valid_facebook_url(url):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Facebook URL: '{url}'. Supported formats include facebook.com/.../posts/..., fb.com/share/p/..., etc.",
        )

    config = ScraperConfig()
    try:
        scraper = FacebookScraper(config=config, headless=req.headless)
        async with scraper:
            result = await scraper.scrape_post(url)
        return result
    except Exception as e:
        logger.exception("Scraping failed")
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")


@app.post("/api/download", response_model=DownloadResult)
async def api_download_media(req: DownloadRequest):
    """Download scraped media items to local disk."""
    if not req.items:
        raise HTTPException(status_code=400, detail="No media items provided to download.")

    scrape_result = ScrapeResult(
        post_id=req.post_id,
        canonical_url="",
        original_url="",
        items=req.items,
        total_discovered=len(req.items),
    )

    downloader = MediaDownloader()
    try:
        result = await downloader.download_all(
            scrape_result=scrape_result,
            output_dir=req.output_dir,
            concurrency=req.concurrency,
            show_progress=False,
        )
        return result
    except Exception as e:
        logger.exception("Download failed")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.post("/api/download-zip")
async def api_download_zip(req: ZipDownloadRequest):
    """Stream all media items as a single in-memory ZIP archive to the browser."""
    from .cdn_utils import resolve_image_extension

    if not req.items:
        raise HTTPException(status_code=400, detail="No items to download.")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://www.facebook.com/",
    }

    zip_buffer = io.BytesIO()
    semaphore = asyncio.Semaphore(10)

    async with httpx.AsyncClient(
        headers=headers,
        timeout=httpx.Timeout(45.0),
        follow_redirects=True,
        limits=httpx.Limits(max_connections=30),
    ) as client:
        async def fetch_item(idx: int, item: MediaItem):
            async with semaphore:
                for attempt in range(1, 4):
                    try:
                        resp = await client.get(item.url)
                        if resp.status_code == 200:
                            content_type = resp.headers.get("content-type", "image/jpeg")
                            ext = resolve_image_extension(
                                url=item.url,
                                content_type=content_type,
                                magic_bytes=resp.content[:64],
                            )
                            filename = f"photo_{idx:03d}{ext}"
                            return filename, resp.content
                    except Exception as e:
                        logger.warning(f"Error fetching photo #{idx} for ZIP (attempt {attempt}): {e}")
                        await asyncio.sleep(0.3 * attempt)
                return None

        tasks = [fetch_item(idx, item) for idx, item in enumerate(req.items, start=1)]
        results = await asyncio.gather(*tasks)

        import re
        clean_folder = re.sub(r'[^\w\s-]', '', req.folder_name).strip().replace(" ", "_") if req.folder_name else None

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for res in results:
                if res:
                    filename, content = res
                    zip_entry_path = f"{clean_folder}/{filename}" if clean_folder else filename
                    zip_file.writestr(zip_entry_path, content)

    zip_buffer.seek(0)
    default_name = f"facebook_{req.post_id or 'photos'}"
    zip_filename = f"{clean_folder or default_name}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


@app.get("/api/download-single")
async def api_download_single(url: str, filename: Optional[str] = None):
    """Proxy and stream a single image directly to the client browser with download attachment headers."""
    if not url:
        raise HTTPException(status_code=400, detail="Missing image URL parameter.")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Referer": "https://www.facebook.com/",
    }

    try:
        async with httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(30.0), follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Failed to fetch image from CDN.")

            content_type = resp.headers.get("content-type", "image/jpeg")
            ext = resolve_image_extension(url=url, content_type=content_type, magic_bytes=resp.content[:64])

            clean_name = filename or f"facebook_photo{ext}"
            if not clean_name.endswith(ext):
                clean_name = f"{clean_name.rsplit('.', 1)[0]}{ext}"

            return StreamingResponse(
                io.BytesIO(resp.content),
                media_type=content_type,
                headers={"Content-Disposition": f'attachment; filename="{clean_name}"'},
            )
    except Exception as e:
        logger.warning(f"Failed to stream single download: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@app.post("/api/open-folder")
async def api_open_folder(req: OpenFolderRequest):
    """Open downloaded folder in the host OS file explorer (e.g. macOS Finder)."""
    target_path = Path(req.path).expanduser().resolve()
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Directory does not exist.")

    system = platform.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.run(["open", str(target_path)], check=True)
        elif system == "Windows":
            os.startfile(str(target_path))  # type: ignore
        else:  # Linux / Unix
            subprocess.run(["xdg-open", str(target_path)], check=True)
        return {"success": True, "path": str(target_path)}
    except Exception as e:
        logger.exception("Failed to open directory")
        raise HTTPException(status_code=500, detail=f"Failed to open directory: {str(e)}")


# Serve Web UI Single Page App
if (WEB_DIR / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


@app.api_route("/", methods=["GET", "HEAD"])
async def serve_index():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "Web UI is initializing. Please create index.html in the web/ directory."}


@app.api_route("/tutorial", methods=["GET", "HEAD"])
async def serve_tutorial():
    tutorial_file = WEB_DIR / "tutorial.html"
    if tutorial_file.exists():
        return FileResponse(tutorial_file)
    return {"message": "Tutorial page not found."}
