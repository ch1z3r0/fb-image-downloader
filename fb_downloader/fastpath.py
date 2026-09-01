"""Fast-Path Async HTTP Scraper for extracting full-resolution Facebook post images."""

import asyncio
import html
import json
import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from .cdn_utils import (
    clean_cdn_url,
    detect_extension_from_url,
    extract_photo_key,
    is_valid_cdn_image_url,
)
from .config import AVATAR_PATTERN_SUBSTRINGS, BLOCKED_CDN_PATTERNS
from .models import MediaItem, PostMetadata, ScrapeResult
from .url_utils import extract_post_id, normalize_facebook_url

logger = logging.getLogger("fb_downloader.fastpath")

# Additional low-res patterns to ensure only full-resolution images are selected
LOW_RES_PATTERNS: Tuple[str, ...] = (
    *AVATAR_PATTERN_SUBSTRINGS,
    "s150x150",
    "s160x160",
    "p160x160",
    "s320x320",
    "p320x320",
    "s240x240",
    "p240x240",
    "_s.jpg",
    "_t.jpg",
    "_q.jpg",
    "_a.jpg",
    "c0.0.150.150",
    "c0.0.320.320",
)


class FastPathExtractor:
    """High-performance async HTTP scraper that extracts high-res Facebook CDN links directly from raw HTML and inline Relay/GraphQL payloads."""

    def __init__(self, timeout_seconds: float = 15.0):
        self.timeout = timeout_seconds
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
        }

    async def extract(self, url: str) -> Optional[ScrapeResult]:
        """Attempt fast-path extraction of high-resolution images from the given Facebook post URL."""
        canonical_url, post_id = normalize_facebook_url(url)
        logger.info(f"[FastPath] Attempting fast HTTP extraction for: {canonical_url} (Post ID: {post_id})")

        try:
            async with httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                limits=httpx.Limits(max_connections=20),
            ) as client:
                resp = await client.get(canonical_url)
                if resp.status_code != 200:
                    logger.debug(f"[FastPath] HTTP status {resp.status_code} for {canonical_url}")
                    return None

                html_text = resp.text
                if not html_text:
                    return None

                # Check for post deletion or privacy restrictions
                is_private_or_deleted, status_msg = self._check_unavailability(html_text)
                if is_private_or_deleted:
                    logger.warning(f"[FastPath] Post {post_id} is private or removed: {status_msg}")
                    return ScrapeResult(
                        post_id=post_id,
                        canonical_url=canonical_url,
                        original_url=url,
                        items=[],
                        total_discovered=0,
                        metadata=PostMetadata(
                            post_id=post_id,
                            canonical_url=canonical_url,
                            original_url=url,
                        ),
                        is_private_or_deleted=True,
                        status_message=status_msg,
                    )

                discovered_items: List[MediaItem] = []
                seen_urls: Set[str] = set()

                # 1. Parse OpenGraph and Meta tags
                meta_items = self._extract_from_meta_tags(html_text)
                for item in meta_items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        discovered_items.append(item)

                # 2. Parse inline Relay and GraphQL JSON scripts
                json_items = self._extract_from_inline_json(html_text)
                for item in json_items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        discovered_items.append(item)

                # 3. Parse unescaped raw CDN strings matching full-size patterns
                regex_items = self._extract_from_raw_cdn_patterns(html_text)
                for item in regex_items:
                    if item.url not in seen_urls:
                        seen_urls.add(item.url)
                        discovered_items.append(item)

                # Filter low-resolution variants and deduplicate by photo key
                final_items = self._filter_and_deduplicate(discovered_items)

                if not final_items:
                    logger.debug(f"[FastPath] No high-resolution images parsed via HTTP fast-path for {post_id}")
                    return None

                # Re-index items
                for idx, itm in enumerate(final_items, start=1):
                    itm.index = idx
                    if not itm.suggested_filename:
                        itm.suggested_filename = f"photo_{idx:03d}"

                metadata = PostMetadata(
                    post_id=post_id,
                    canonical_url=canonical_url,
                    original_url=url,
                    is_multi_photo=len(final_items) > 1,
                )

                logger.info(
                    f"[FastPath] Successfully extracted {len(final_items)} high-res photo(s) in fast-path (Post ID: {post_id})"
                )

                return ScrapeResult(
                    post_id=post_id,
                    canonical_url=canonical_url,
                    original_url=url,
                    items=final_items,
                    total_discovered=len(final_items),
                    metadata=metadata,
                    is_private_or_deleted=False,
                    status_message=None,
                )

        except Exception as e:
            logger.debug(f"[FastPath] Fast extraction encountered exception: {e}")
            return None

    def _check_unavailability(self, html_text: str) -> Tuple[bool, Optional[str]]:
        """Detect if post is private, restricted, or deleted."""
        unavailable_indicators = [
            "content isn't available right now",
            "this content isn't available",
            "page isn't available",
            "the link you followed may be broken, or the page may have been removed",
            "only shared it with a small group of people",
            "this page isn't available right now",
            "may have been deleted",
        ]
        text_lower = html_text.lower()
        for ind in unavailable_indicators:
            if ind in text_lower:
                return (
                    True,
                    "This Facebook post is private, restricted, or has been removed by its owner. "
                    "Facebook requires you to be logged into an authorized account to view it.",
                )
        return False, None

    def _extract_from_meta_tags(self, html_text: str) -> List[MediaItem]:
        """Extract image URLs from OpenGraph and standard HTML meta tags."""
        items: List[MediaItem] = []
        meta_patterns = [
            r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
            r'<meta\s+property=["\']og:image:url["\']\s+content=["\']([^"\']+)["\']',
            r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image:url["\']',
            r'<link\s+rel=["\']image_src["\']\s+href=["\']([^"\']+)["\']',
        ]

        for pat in meta_patterns:
            matches = re.findall(pat, html_text, re.IGNORECASE)
            for m in matches:
                url_str = self._unescape_url(m)
                if self._is_valid_high_res_url(url_str):
                    items.append(MediaItem(url=url_str))

        return items

    def _extract_from_inline_json(self, html_text: str) -> List[MediaItem]:
        """Extract high-resolution media URLs and dimension pairs from inline Relay/GraphQL script tags."""
        items: List[MediaItem] = []

        # Find script tags containing JSON payloads or Relay stream caches
        script_matches = re.findall(
            r'<script[^>]*>(.*?)</script>',
            html_text,
            re.DOTALL | re.IGNORECASE,
        )

        for script_content in script_matches:
            if not script_content or ("scontent" not in script_content and "fbcdn.net" not in script_content):
                continue

            # Look for structured image JSON patterns: {"uri": "...", "width": ..., "height": ...}
            image_obj_matches = re.findall(
                r'\{[^{}]*?"uri"\s*:\s*"([^"]+)"[^{}]*?\}',
                script_content,
            )

            for img_match in image_obj_matches:
                uri = self._unescape_url(img_match)
                if self._is_valid_high_res_url(uri):
                    # Try to extract width and height from surrounding context if available
                    width, height = self._extract_dimensions_from_json_snippet(script_content, img_match)
                    items.append(MediaItem(url=uri, width=width, height=height))

            # Look for "photo_image", "full_res_image", "viewer_image", "progressive_image" keys
            key_patterns = [
                r'"(?:photo_image|full_res_image|viewer_image|large_share_image|progressive_image|scaled_image)"\s*:\s*\{[^}]*?"uri"\s*:\s*"([^"]+)"',
                r'"image"\s*:\s*\{[^}]*?"uri"\s*:\s*"([^"]+)"',
            ]
            for kp in key_patterns:
                for match in re.findall(kp, script_content):
                    uri = self._unescape_url(match)
                    if self._is_valid_high_res_url(uri):
                        items.append(MediaItem(url=uri))

        return items

    def _extract_from_raw_cdn_patterns(self, html_text: str) -> List[MediaItem]:
        """Regex parse unescaped raw CDN strings matching scontent URLs."""
        items: List[MediaItem] = []

        # Matches scontent URLs in raw HTML / JS payloads
        raw_cdn_patterns = [
            r'https:\\/\\/scontent[^"\'\s<>]+',
            r'https://scontent[^"\'\s<>]+',
            r'https:\\/\\/[a-z0-9.-]+\.fbcdn\.net\\/[^"\'\s<>]+',
            r'https://[a-z0-9.-]+\.fbcdn\.net/[^"\'\s<>]+',
        ]

        for pat in raw_cdn_patterns:
            matches = re.findall(pat, html_text)
            for m in matches:
                url_str = self._unescape_url(m)
                if self._is_valid_high_res_url(url_str):
                    items.append(MediaItem(url=url_str))

        return items

    def _extract_dimensions_from_json_snippet(self, content: str, uri_match: str) -> Tuple[Optional[int], Optional[int]]:
        """Attempt to extract width and height from adjacent JSON properties."""
        try:
            pos = content.find(uri_match)
            if pos != -1:
                start = max(0, pos - 120)
                end = min(len(content), pos + len(uri_match) + 120)
                snippet = content[start:end]

                w_match = re.search(r'"width"\s*:\s*(\d+)', snippet)
                h_match = re.search(r'"height"\s*:\s*(\d+)', snippet)

                width = int(w_match.group(1)) if w_match else None
                height = int(h_match.group(1)) if h_match else None
                return width, height
        except Exception:
            pass
        return None, None

    def _unescape_url(self, raw_url: str) -> str:
        """Unescape JSON and HTML encoded characters in URL strings."""
        if not raw_url:
            return ""
        url = raw_url.replace(r"\/", "/").replace(r"\u0026", "&")
        url = html.unescape(url)
        return clean_cdn_url(url)

    def _is_valid_high_res_url(self, url: str) -> bool:
        """Filter out low-resolution variants (avatars, small thumbnails, emojis, tracking pixels)."""
        if not is_valid_cdn_image_url(url):
            return False

        url_lower = url.lower()

        # Reject any URL matching low-resolution markers
        for pat in LOW_RES_PATTERNS:
            if pat in url_lower:
                return False

        # Reject profile pictures or small icons
        if "/p50x50/" in url_lower or "/s150x150/" in url_lower or "/s320x320/" in url_lower:
            return False

        return True

    def _filter_and_deduplicate(self, items: List[MediaItem]) -> List[MediaItem]:
        """Group by unique photo key and keep the highest-resolution variant."""
        unique_map: Dict[str, MediaItem] = {}

        for item in items:
            # If dimensions are present and both are < 250px, skip as thumbnail/avatar
            if item.width and item.height and item.width < 250 and item.height < 250:
                continue

            key = extract_photo_key(item.url)
            if key not in unique_map:
                unique_map[key] = item
            else:
                existing = unique_map[key]
                ex_area = (existing.width or 0) * (existing.height or 0)
                new_area = (item.width or 0) * (item.height or 0)
                if new_area > ex_area:
                    unique_map[key] = item
                elif new_area == ex_area:
                    # Prefer clean URL over complex query parameters
                    if len(item.url) < len(existing.url):
                        unique_map[key] = item

        return list(unique_map.values())
