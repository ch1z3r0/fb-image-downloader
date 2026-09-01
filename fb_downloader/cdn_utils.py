"""CDN asset filtering, srcset resolution parsing, and MIME-type mapping."""

import html
import re
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from .config import AVATAR_PATTERN_SUBSTRINGS, BLOCKED_CDN_PATTERNS

MIME_EXTENSION_MAP = {
    # JPEG formats
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/jfif": ".jpg",
    # PNG formats
    "image/png": ".png",
    "image/x-png": ".png",
    # WebP format
    "image/webp": ".webp",
    # Next-Gen AVIF & HEIC formats
    "image/avif": ".avif",
    "image/avis": ".avif",
    "image/heic": ".heic",
    "image/heic-sequence": ".heic",
    "image/heif": ".heif",
    "image/heif-sequence": ".heif",
    # GIF format
    "image/gif": ".gif",
    # BMP formats
    "image/bmp": ".bmp",
    "image/x-ms-bmp": ".bmp",
    "image/x-bmp": ".bmp",
    # TIFF formats
    "image/tiff": ".tiff",
    "image/x-tiff": ".tiff",
    # Vector & Icon formats
    "image/svg+xml": ".svg",
    "image/x-icon": ".ico",
    "image/vnd.microsoft.icon": ".ico",
    # JPEG XL
    "image/jxl": ".jxl",
}


def is_valid_cdn_image_url(url: str) -> bool:
    """Check if a URL represents a genuine post photo and not an avatar or UI element."""
    if not url or not isinstance(url, str):
        return False

    url_lower = url.lower().strip()

    # Must be valid http/https
    if not url_lower.startswith(("http://", "https://")):
        return False

    # Filter out blocked patterns (emojis, sprites, tracking beacons)
    for pattern in BLOCKED_CDN_PATTERNS:
        if pattern in url_lower:
            return False

    # Filter out small avatar thumbnails
    for avatar_pat in AVATAR_PATTERN_SUBSTRINGS:
        if avatar_pat in url_lower:
            return False

    # Must usually come from fbcdn or have image characteristics
    is_fb_cdn = any(
        domain in url_lower
        for domain in ("fbcdn.net", "akamaihd.net", "facebook.com", "instagram.com")
    )
    has_img_ext = any(
        ext in url_lower
        for ext in (
            ".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif", ".gif", ".bmp", ".tiff", ".svg",
            "dst-jpg", "dst-png", "dst-webp", "dst-avif"
        )
    )

    return is_fb_cdn or has_img_ext


def parse_srcset_largest(srcset: str) -> Optional[str]:
    """Parse an HTML srcset attribute and return the highest-resolution URL."""
    if not srcset:
        return None

    entries = srcset.split(",")
    best_url = None
    best_score = -1.0

    for entry in entries:
        parts = entry.strip().split()
        if not parts:
            continue
        candidate_url = html.unescape(parts[0])

        score = 1.0
        if len(parts) > 1:
            descriptor = parts[1].strip()
            if descriptor.endswith("w"):
                try:
                    score = float(descriptor[:-1])
                except ValueError:
                    score = 1.0
            elif descriptor.endswith("x"):
                try:
                    score = float(descriptor[:-1]) * 1000.0
                except ValueError:
                    score = 1.0

        if score > best_score and is_valid_cdn_image_url(candidate_url):
            best_score = score
            best_url = candidate_url

    return best_url


def clean_cdn_url(url: str) -> str:
    """Clean and unescape Facebook CDN URL while preserving authorization tokens."""
    if not url:
        return ""
    # Unescape HTML entities (e.g., &amp; -> &)
    cleaned = html.unescape(url.strip())
    return cleaned


def detect_extension_from_url(url: str, default: str = ".jpg") -> str:
    """Infer image extension from URL path or Facebook query parameters (e.g. stp=dst-png)."""
    if not url:
        return default

    url_lower = url.lower()

    # 1. Check Facebook format transform parameters (e.g. stp=dst-png, stp=dst-jpg, stp=dst-webp)
    if "dst-png" in url_lower:
        return ".png"
    if "dst-webp" in url_lower:
        return ".webp"
    if "dst-avif" in url_lower:
        return ".avif"
    if "dst-jpg" in url_lower or "dst-jpeg" in url_lower:
        return ".jpg"

    # 2. Check path extension
    try:
        path = urlparse(url).path
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".avif", ".heic", ".heif", ".gif", ".bmp", ".tiff", ".svg", ".ico"):
            if path.lower().endswith(ext):
                return ".jpg" if ext == ".jpeg" else ext
    except Exception:
        pass

    return default


def mime_to_extension(content_type: Optional[str], default: str = ".jpg") -> str:
    """Map HTTP response Content-Type header to standard file extension."""
    if not content_type:
        return default

    # Extract primary mime type (e.g. 'image/jpeg; charset=utf-8' -> 'image/jpeg')
    primary_mime = content_type.split(";")[0].strip().lower()
    return MIME_EXTENSION_MAP.get(primary_mime, default)


def detect_extension_from_bytes(data: bytes, fallback: str = ".jpg") -> str:
    """Detect image file extension with high precision from leading binary magic bytes.
    
    Supports: JPEG, PNG, WebP, GIF, AVIF, HEIC/HEIF, BMP, TIFF, SVG, ICO, JXL.
    """
    if not data or len(data) < 2:
        return fallback

    # JPEG: FF D8 FF
    if len(data) >= 3 and data[:3] == b"\xFF\xD8\xFF":
        return ".jpg"

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"

    # WebP: RIFF ... WEBP
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"

    # GIF: GIF87a or GIF89a
    if len(data) >= 6 and (data[:6] == b"GIF87a" or data[:6] == b"GIF89a"):
        return ".gif"

    # BMP: BM
    if data[:2] == b"BM":
        return ".bmp"

    # TIFF: II*\x00 (little endian) or MM\x00* (big endian)
    if len(data) >= 4 and (data[:4] == b"II*\x00" or data[:4] == b"MM\x00*"):
        return ".tiff"

    # AVIF / HEIC / HEIF / ISO Base Media File Format
    if len(data) >= 12 and data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"avif", b"avis", b"mif1") and b"avif" in data[:32]:
            return ".avif"
        if brand in (b"heic", b"heix", b"heim", b"heis", b"mif1", b"msf1"):
            return ".heic"

    # ICO: 00 00 01 00
    if len(data) >= 4 and data[:4] == b"\x00\x00\x01\x00":
        return ".ico"

    # JPEG XL: FF 0A or Container format
    if (len(data) >= 2 and data[:2] == b"\xFF\x0A") or (len(data) >= 12 and data[:12] == b"\x00\x00\x00\x0CJXL \x0D\x0A\x87\x0A"):
        return ".jxl"

    # SVG: <?xml or <svg
    data_stripped = data.lstrip()
    if data_stripped.startswith(b"<?xml") or data_stripped.startswith(b"<svg"):
        return ".svg"

    return fallback


def resolve_image_extension(
    url: Optional[str] = None,
    content_type: Optional[str] = None,
    magic_bytes: Optional[bytes] = None,
    default: str = ".jpg"
) -> str:
    """Determine the most accurate file extension by cross-referencing bytes, MIME, and URL hints."""
    # 1. Binary magic bytes are the ground truth
    if magic_bytes and len(magic_bytes) >= 2:
        detected = detect_extension_from_bytes(magic_bytes, fallback="")
        if detected:
            return detected

    # 2. HTTP response Content-Type header
    if content_type and "octet-stream" not in content_type.lower():
        mime_ext = mime_to_extension(content_type, default="")
        if mime_ext:
            return mime_ext

    # 3. URL path and Facebook parameters (stp=dst-png, etc.)
    if url:
        url_ext = detect_extension_from_url(url, default="")
        if url_ext:
            return url_ext

    return default


def extract_photo_key(url: str) -> str:
    """Extract unique photo identifier to deduplicate multiple resolution variants of the same photo."""
    if not url:
        return ""
    try:
        path = urlparse(url).path
        filename = path.split("/")[-1]
        parts = filename.split("_")
        # Standard Facebook CDN filename format: <cache_prefix>_<fbid>_<hash>_n.ext
        if len(parts) >= 3 and parts[1].isdigit():
            return parts[1]
        return filename or url
    except Exception:
        return url
