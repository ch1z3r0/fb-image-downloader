"""Tests for CDN URL filtering, srcset resolution, and MIME-type detection."""

import pytest
from fb_downloader.cdn_utils import (
    clean_cdn_url,
    detect_extension_from_bytes,
    is_valid_cdn_image_url,
    mime_to_extension,
    parse_srcset_largest,
)


def test_is_valid_cdn_image_url():
    # Valid high-res CDN URLs
    assert is_valid_cdn_image_url(
        "https://scontent.xx.fbcdn.net/v/t39.30808-6/44556677_n.jpg?_nc_cat=101&ccb=1-7"
    )
    assert is_valid_cdn_image_url(
        "https://scontent-iad3-1.xx.fbcdn.net/v/t1.6435-9/998877_n.png"
    )

    # Invalid URLs (UI icons, sprites, emojis, small avatar thumbnails)
    assert not is_valid_cdn_image_url("https://static.xx.fbcdn.net/rsrc.php/v3/y1/r/icon.png")
    assert not is_valid_cdn_image_url("https://static.xx.fbcdn.net/images/emoji.php/v9/t56/1/16/smile.png")
    assert not is_valid_cdn_image_url("https://scontent.xx.fbcdn.net/v/t39.30808-1/p50x50/avatar.jpg")
    assert not is_valid_cdn_image_url("https://scontent.xx.fbcdn.net/v/t39.30808-1/s32x32/avatar.jpg")
    assert not is_valid_cdn_image_url("data:image/svg+xml;base64,PHN2Zy...")
    assert not is_valid_cdn_image_url("")


def test_parse_srcset_largest():
    srcset = (
        "https://scontent.xx.fbcdn.net/v/img_500.jpg 500w, "
        "https://scontent.xx.fbcdn.net/v/img_2048.jpg 2048w, "
        "https://scontent.xx.fbcdn.net/v/img_1080.jpg 1080w"
    )
    best = parse_srcset_largest(srcset)
    assert best == "https://scontent.xx.fbcdn.net/v/img_2048.jpg"


def test_clean_cdn_url():
    escaped = "https://scontent.xx.fbcdn.net/v/img.jpg?_nc_cat=101&amp;ccb=1-7&amp;oh=abcdef"
    assert clean_cdn_url(escaped) == "https://scontent.xx.fbcdn.net/v/img.jpg?_nc_cat=101&ccb=1-7&oh=abcdef"


def test_mime_to_extension():
    assert mime_to_extension("image/jpeg") == ".jpg"
    assert mime_to_extension("image/png; charset=utf-8") == ".png"
    assert mime_to_extension("image/webp") == ".webp"
    assert mime_to_extension("image/gif") == ".gif"
    assert mime_to_extension("image/avif") == ".avif"
    assert mime_to_extension("image/heic") == ".heic"
    assert mime_to_extension("image/bmp") == ".bmp"
    assert mime_to_extension("image/tiff") == ".tiff"
    assert mime_to_extension(None) == ".jpg"


def test_detect_extension_from_bytes():
    jpeg_bytes = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01"
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    webp_bytes = b"RIFF\x12\x00\x00\x00WEBPVP8 "
    gif_bytes = b"GIF89a\x01\x00\x01\x00\x80\x00\x00"
    bmp_bytes = b"BM\x36\x00\x00\x00\x00\x00"
    tiff_bytes = b"II*\x00\x08\x00\x00\x00"
    avif_bytes = b"\x00\x00\x00\x1cftypavif\x00\x00\x00\x00avifmif1"
    heic_bytes = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic"
    svg_bytes = b"<svg xmlns='http://www.w3.org/2000/svg' width='100' height='100'></svg>"

    assert detect_extension_from_bytes(jpeg_bytes) == ".jpg"
    assert detect_extension_from_bytes(png_bytes) == ".png"
    assert detect_extension_from_bytes(webp_bytes) == ".webp"
    assert detect_extension_from_bytes(gif_bytes) == ".gif"
    assert detect_extension_from_bytes(bmp_bytes) == ".bmp"
    assert detect_extension_from_bytes(tiff_bytes) == ".tiff"
    assert detect_extension_from_bytes(avif_bytes) == ".avif"
    assert detect_extension_from_bytes(heic_bytes) == ".heic"
    assert detect_extension_from_bytes(svg_bytes) == ".svg"
    assert detect_extension_from_bytes(b"invalid data string") == ".jpg"


def test_resolve_image_extension():
    from fb_downloader.cdn_utils import resolve_image_extension

    # 1. By bytes
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    assert resolve_image_extension(url="https://fbcdn.net/p.jpg", magic_bytes=png_bytes) == ".png"

    # 2. By MIME
    assert resolve_image_extension(content_type="image/webp") == ".webp"
    assert resolve_image_extension(content_type="image/avif") == ".avif"

    # 3. By URL hints
    assert resolve_image_extension(url="https://fbcdn.net/photo?stp=dst-png_s1080x1080") == ".png"
    assert resolve_image_extension(url="https://fbcdn.net/photo?stp=dst-webp_s1080x1080") == ".webp"
