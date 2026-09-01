"""Tests for concurrent chunked media downloader."""

import os
import pytest
import httpx
from fb_downloader.downloader import MediaDownloader
from fb_downloader.models import MediaItem, ScrapeResult


@pytest.mark.asyncio
async def test_downloader_success(tmp_path):
    # Setup test dummy data
    img_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 1024

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "image/png", "Content-Length": str(len(img_data))},
            content=img_data,
        )

    transport = httpx.MockTransport(handler)

    downloader = MediaDownloader()
    items = [
        MediaItem(url="https://mock.cdn/photo1", index=1, suggested_filename="photo_001"),
        MediaItem(url="https://mock.cdn/photo2", index=2, suggested_filename="photo_002"),
    ]
    scrape_result = ScrapeResult(
        post_id="test_post_123",
        canonical_url="https://www.facebook.com/test_post_123",
        original_url="https://www.facebook.com/test_post_123",
        items=items,
        total_discovered=2,
    )

    # Patch client creation or call download single with transport
    output_dir = tmp_path / "downloads" / "test_post_123"

    async with httpx.AsyncClient(transport=transport) as client:
        results = []
        for idx, itm in enumerate(items, start=1):
            res = await downloader._download_single(
                client=client,
                item=itm,
                index=idx,
                target_dir=output_dir,
            )
            results.append(res)

    assert len(results) == 2
    assert results[0].suggested_filename == "photo_001.png"
    assert results[1].suggested_filename == "photo_002.png"
    assert os.path.exists(output_dir / "photo_001.png")
    assert os.path.exists(output_dir / "photo_002.png")
    assert os.path.getsize(output_dir / "photo_001.png") == len(img_data)


@pytest.mark.asyncio
async def test_downloader_empty_result(tmp_path):
    downloader = MediaDownloader()
    scrape_result = ScrapeResult(
        post_id="empty_post",
        canonical_url="https://www.facebook.com/empty",
        original_url="https://www.facebook.com/empty",
        items=[],
        total_discovered=0,
    )
    result = await downloader.download_all(
        scrape_result=scrape_result,
        output_dir=str(tmp_path),
        show_progress=False,
    )
    assert len(result.successful_items) == 0
    assert len(result.failed_items) == 0
    assert result.total_bytes == 0


@pytest.mark.asyncio
async def test_downloader_multi_format_and_custom_dir(tmp_path):
    webp_data = b"RIFF\x1a\x00\x00\x00WEBPVP8 " + b"\x00" * 500
    avif_data = b"\x00\x00\x00\x1cftypavif\x00\x00\x00\x00avifmif1" + b"\x00" * 300

    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        if "webp_photo" in url_str:
            return httpx.Response(
                status_code=200,
                headers={"Content-Type": "image/webp"},
                content=webp_data,
            )
        else:
            return httpx.Response(
                status_code=200,
                headers={"Content-Type": "image/avif"},
                content=avif_data,
            )

    transport = httpx.MockTransport(handler)
    downloader = MediaDownloader()

    items = [
        MediaItem(url="https://mock.cdn/webp_photo", index=1),
        MediaItem(url="https://mock.cdn/avif_photo", index=2),
    ]

    custom_dir = tmp_path / "my_custom_photos"

    async with httpx.AsyncClient(transport=transport) as client:
        res1 = await downloader._download_single(client, items[0], 1, custom_dir)
        res2 = await downloader._download_single(client, items[1], 2, custom_dir)

    assert res1.suggested_filename.endswith(".webp")
    assert res2.suggested_filename.endswith(".avif")
    assert os.path.exists(custom_dir / res1.suggested_filename)
    assert os.path.exists(custom_dir / res2.suggested_filename)
