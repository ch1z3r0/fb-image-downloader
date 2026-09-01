"""URL utilities for validating, normalizing, and parsing Facebook links."""

import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def is_valid_facebook_url(url: str) -> bool:
    """Check if a URL is a valid Facebook endpoint."""
    if not url or not isinstance(url, str):
        return False
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return False

    netloc = parsed.netloc.lower().split(":")[0]  # strip port if present
    valid_domains = ("facebook.com", "fb.com", "fb.watch", "fb.me")
    return any(netloc == d or netloc.endswith("." + d) for d in valid_domains)


def extract_post_id(url: str) -> str:
    """Extract a post ID or media identifier from a Facebook URL."""
    if not url:
        return "unknown_post"

    clean_url = url.strip()
    parsed = urlparse(clean_url)
    path = parsed.path
    query_params = parse_qs(parsed.query)

    # 1. Query param story_fbid or fbid
    if "story_fbid" in query_params:
        return query_params["story_fbid"][0]
    if "fbid" in query_params:
        return query_params["fbid"][0]

    # 2. Path patterns
    # /share/p/<id>/ or /share/v/<id>/
    share_match = re.search(r"/share/(?:p|v)/([a-zA-Z0-9_-]+)", path)
    if share_match:
        return share_match.group(1)

    # /posts/<id> or /posts/pcb.<id>
    posts_match = re.search(r"/posts/(?:pcb\.)?(\d+|[a-zA-Z0-9_-]+)", path)
    if posts_match:
        return posts_match.group(1)

    # /photos/.../<id> or /photo/<id>
    photos_match = re.search(r"/photos/(?:[a-zA-Z0-9_.-]+/)?(\d+)", path)
    if photos_match:
        return photos_match.group(1)

    # /media/set/?set=a.<id>
    if "set" in query_params:
        set_val = query_params["set"][0]
        set_clean = set_val.replace("a.", "").replace("pcb.", "")
        return set_clean

    # Fallback to last alphanumeric path segment or hash
    path_parts = [p for p in path.strip("/").split("/") if p]
    if path_parts:
        last_segment = path_parts[-1]
        if last_segment not in ("photo", "photo.php", "permalink.php", "story.php"):
            return re.sub(r"[^a-zA-Z0-9_-]", "", last_segment) or "facebook_post"

    return "facebook_post"


def normalize_facebook_url(url: str) -> Tuple[str, str]:
    """Normalize a Facebook URL to canonical desktop format and extract post_id.

    Returns:
        Tuple of (canonical_url, post_id)
    """
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = "https://" + clean_url

    parsed = urlparse(clean_url)
    # Standardize hostname
    netloc = "www.facebook.com"
    path = parsed.path
    query = parsed.query

    # Keep essential query params if needed
    query_params = parse_qs(query)
    kept_params = {}
    for key in ("fbid", "story_fbid", "id", "set", "vanity"):
        if key in query_params:
            kept_params[key] = query_params[key][0]

    new_query = urlencode(kept_params) if kept_params else ""
    canonical_url = urlunparse(
        ("https", netloc, path, "", new_query, "")
    )
    post_id = extract_post_id(clean_url)
    return canonical_url, post_id
