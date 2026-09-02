"""Configuration and selector registry for Facebook Image Downloader."""

from dataclasses import dataclass
from typing import List, Tuple


@dataclass(frozen=True)
class ScraperConfig:
    """Scraper operational settings."""

    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1920
    viewport_height: int = 1080
    locale: str = "en-US"
    timezone: str = "America/New_York"
    page_timeout_ms: int = 40000
    navigation_timeout_ms: int = 35000
    modal_wait_ms: int = 2000
    carousel_max_steps: int = 2500


@dataclass(frozen=True)
class DownloaderConfig:
    """Downloader operational settings."""

    chunk_size: int = 65536  # 64 KB
    default_concurrency: int = 5
    max_retries: int = 3
    timeout_seconds: float = 30.0
    default_output_root: str = "./downloads"


# Selectors to dismiss Facebook cookie and login dialogs
COOKIE_CONSENT_SELECTORS: List[str] = [
    '[data-cookiebanner="accept_button"]',
    '[aria-label="Allow all cookies"]',
    '[aria-label="Accept all"]',
    '[aria-label="Allow essential and optional cookies"]',
    '[aria-label="Decline optional cookies"]',
    '[aria-label="Only allow essential cookies"]',
    'button:has-text("Allow all cookies")',
    'button:has-text("Accept all")',
    'button:has-text("Allow essential and optional cookies")',
    'button:has-text("Decline optional cookies")',
    'button:has-text("Only allow essential cookies")',
]

LOGIN_MODAL_CLOSE_SELECTORS: List[str] = [
    'div[role="dialog"] [aria-label="Close"]',
    'div[role="dialog"] [aria-label="close"]',
    'div[aria-label="Close"]',
    'div[aria-label="close"]',
    '[data-testid="royal_login_button"] ~ div [aria-label="Close"]',
]

# Photo & Theater view selectors
THEATER_IMAGE_SELECTORS: List[str] = [
    'div[data-visualcompletion="media-vc-image"] img',
    'img[data-visualcompletion="media-vc-image"]',
    'div[role="dialog"] img[data-visualcompletion="media-vc-image"]',
    'div[role="dialog"] img[src*="fbcdn.net"]',
    'div[role="main"] img[src*="fbcdn.net"]',
    'img.spotlight',
]

THEATER_NEXT_BUTTON_SELECTORS: List[str] = [
    '[aria-label="Next photo"]',
    '[aria-label="Next image"]',
    '[aria-label="Next"]',
    'div[aria-label="Next photo"]',
    'div[aria-label="Next image"]',
    'div[aria-label="Next"]',
    'div[role="dialog"] [aria-label="Next photo"]',
    'div[role="dialog"] [aria-label="Next image"]',
    'div[role="dialog"] [aria-label="Next"]',
    'a[aria-label="Next"]',
]

# Grid / Thumbnail selectors
PHOTO_THUMBNAIL_SELECTORS: List[str] = [
    'a[href*="/photo/?fbid="]',
    'a[href*="/photo.php?fbid="]',
    'a[href*="/photo?fbid="]',
    'a[href*="/photos/"]',
    'div[data-pagelet*="FeedUnit"] a[href*="/photo"]',
    'div[role="article"] a[href*="/photo"]',
    'div[data-pagelet*="PhotoGrid"] a',
]

# CDN Filter keywords and patterns (URLs containing these should be rejected)
BLOCKED_CDN_PATTERNS: Tuple[str, ...] = (
    "/rsrc.php/",
    "/emoji.php/",
    "static.xx.fbcdn.net/rsrc.php",
    "static.xx.fbcdn.net/images/emoji",
    "/m1/v/t6/",
    "/images/icons/",
    "tracking",
    "beacon",
    "pixel",
    "data:image/svg",
    "blank.gif",
    "spacer.gif",
    "hads-ak-",
    "/emg1/v/",
    "t39.1997-6",  # Comment stickers
    "/giphy.",
)

# Avatar dimension markers & profile patterns to filter out user avatars
AVATAR_PATTERN_SUBSTRINGS: Tuple[str, ...] = (
    "-1/",  # e.g., t39.30808-1/ (Profile/comment avatars)
    "p32x32",
    "p50x50",
    "s32x32",
    "s50x50",
    "s60x60",
    "s75x75",
    "s100x100",
    "p100x100",
    "q75_p50x50",
    "q75_p32x32",
    "q75_p60x60",
    "q75_p75x75",
    "q75_p100x100",
    "c0.0.50.50",
    "c0.0.100.100",
)
