"""Playwright-based Facebook Scraper for extracting high-resolution media."""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .cdn_utils import (
    clean_cdn_url,
    extract_photo_key,
    is_valid_cdn_image_url,
    parse_srcset_largest,
)
from .config import (
    COOKIE_CONSENT_SELECTORS,
    LOGIN_MODAL_CLOSE_SELECTORS,
    PHOTO_THUMBNAIL_SELECTORS,
    THEATER_IMAGE_SELECTORS,
    THEATER_NEXT_BUTTON_SELECTORS,
    ScraperConfig,
)
from .models import MediaItem, PostMetadata, ScrapeResult
from .url_utils import extract_post_id, normalize_facebook_url

logger = logging.getLogger("fb_downloader.scraper")


class FacebookScraper:
    """Automates Chromium browser to extract Facebook post images."""

    def __init__(self, config: Optional[ScraperConfig] = None, headless: bool = True):
        self.config = config or ScraperConfig()
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self) -> None:
        """Launch Playwright browser with stealth configurations."""
        if self._browser:
            return

        logger.debug("Initializing Playwright Chromium instance...")
        self._playwright = await async_playwright().start()

        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--lang=en-US,en",
        ]

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=launch_args,
        )

        self._context = await self._browser.new_context(
            user_agent=self.config.user_agent,
            viewport={"width": self.config.viewport_width, "height": self.config.viewport_height},
            locale=self.config.locale,
            timezone_id=self.config.timezone,
            has_touch=False,
            is_mobile=False,
        )

        # Anti-detection script to hide navigator.webdriver
        await self._context.add_init_script(
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            window.chrome = {
                runtime: {}
            };
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            """
        )

    async def close(self) -> None:
        """Gracefully terminate browser context and Playwright instance."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.debug("Playwright browser closed.")

    async def scrape_post(self, url: str) -> ScrapeResult:
        """Main scraping workflow for a given Facebook post URL."""
        if not self._context:
            await self.start()

        canonical_url, post_id = normalize_facebook_url(url)
        logger.info(f"Navigating to Facebook post: {canonical_url} (Post ID: {post_id})")

        page: Page = await self._context.new_page()
        page.set_default_timeout(self.config.page_timeout_ms)

        discovered_items: List[MediaItem] = []
        seen_urls: Set[str] = set()
        intercepted_network_urls: Set[str] = set()

        # 1. Attach live network response interceptor
        def handle_response(response):
            try:
                url_str = response.url
                if "fbcdn.net" in url_str:
                    cleaned = clean_cdn_url(url_str)
                    if is_valid_cdn_image_url(cleaned):
                        intercepted_network_urls.add(cleaned)
            except Exception:
                pass

        page.on("response", handle_response)

        try:
            # 2. Navigate to target post
            try:
                await page.goto(
                    canonical_url,
                    wait_until="domcontentloaded",
                    timeout=self.config.navigation_timeout_ms,
                )
            except Exception as e:
                logger.debug(f"Navigation warning: {e}. Continuing DOM extraction...")

            await asyncio.sleep(1.5)

            # 3. Dismiss cookie consent and login banners cleanly without deleting post containers
            await self._dismiss_modals_and_overlays(page)

            # 4. Scroll slightly to trigger lazy-load rendering of photo grids
            try:
                await page.evaluate("window.scrollBy(0, 600);")
                await asyncio.sleep(1.5)
            except Exception:
                pass

            # 5. Strategy A: Extract high-res media from DOM <img> elements
            dom_items = await self._extract_from_dom_images(page)

            logger.debug(f"DOM strategy found {len(dom_items)} images.")

            # 6. Strategy B: Extract full album grid via media set page if present
            set_items = await self._extract_via_media_set(page)

            logger.debug(f"Media set strategy found {len(set_items)} images.")

            # 7. Strategy C: Theater carousel — walks photos in Facebook's original post order
            theater_items = await self._extract_via_theater_carousel(page)

            logger.debug(f"Theater carousel found {len(theater_items)} images (original post order).")

            # 8. Strategy D: Extract high-res media from embedded JSON scripts
            json_items = await self._extract_from_json_scripts(page)

            logger.debug(f"JSON strategy found {len(json_items)} images.")

            # --- Merge with order preservation ---
            # Priority: theater carousel defines the canonical order (it literally walks left→right
            # in the post). Other strategies add any photos the carousel missed (appended at end).
            #
            # Build a photo-key → best item map from ALL strategies first (for resolution upgrades),
            # then reconstruct the final list in carousel order followed by extras.

            # Step 1: collect all candidates into a best-resolution map
            all_candidates: List[MediaItem] = [
                *theater_items,
                *dom_items,
                *set_items,
                *json_items,
            ]
            for net_url in intercepted_network_urls:
                if is_valid_cdn_image_url(net_url):
                    all_candidates.append(MediaItem(url=net_url))

            best_by_key: Dict[str, MediaItem] = {}
            for itm in all_candidates:
                key = extract_photo_key(itm.url)
                if not key:
                    continue
                if key not in best_by_key:
                    best_by_key[key] = itm
                else:
                    existing = best_by_key[key]
                    ex_area = (existing.width or 0) * (existing.height or 0)
                    new_area = (itm.width or 0) * (itm.height or 0)
                    if new_area > ex_area:
                        best_by_key[key] = itm

            # Step 2: lay out in carousel order first
            ordered_keys: List[str] = []
            seen_keys: Set[str] = set()

            for itm in theater_items:
                k = extract_photo_key(itm.url)
                if k and k not in seen_keys:
                    seen_keys.add(k)
                    ordered_keys.append(k)

            # Step 3: append extras from other strategies (not in carousel) at the end
            for itm in (*dom_items, *set_items, *json_items):
                k = extract_photo_key(itm.url)
                if k and k not in seen_keys and k in best_by_key:
                    seen_keys.add(k)
                    ordered_keys.append(k)

            # Step 4: handle any network-intercepted items with no photo key (rare)
            keyless_items: List[MediaItem] = []
            for net_url in intercepted_network_urls:
                cleaned = clean_cdn_url(net_url)
                k = extract_photo_key(cleaned)
                if not k and is_valid_cdn_image_url(cleaned) and cleaned not in seen_urls:
                    seen_urls.add(cleaned)
                    keyless_items.append(MediaItem(url=cleaned))

            final_items = [best_by_key[k] for k in ordered_keys] + keyless_items

            # Re-index items in their final order
            for idx, itm in enumerate(final_items, start=1):
                itm.index = idx
                if not itm.suggested_filename:
                    itm.suggested_filename = f"photo_{idx:03d}"

            # Post metadata
            metadata = PostMetadata(
                post_id=post_id,
                canonical_url=canonical_url,
                original_url=url,
                is_multi_photo=len(final_items) > 1,
            )

            is_private_or_deleted = False
            status_message = None

            if len(final_items) == 0:
                try:
                    page_text = await page.evaluate("() => document.body ? document.body.innerText : ''")
                    unavailable_indicators = [
                        "content isn't available",
                        "page isn't available",
                        "broken, or the page may have been removed",
                        "only shared it with a small group",
                        "been deleted",
                        "មិនមាន​ខ្លឹមសារនេះទេ",
                        "មិនអាចរកឃើញទំព័រនេះទេ",
                        "ត្រូវបានលុប",
                    ]
                    if any(ind in page_text for ind in unavailable_indicators):
                        is_private_or_deleted = True
                        status_message = (
                            "This Facebook post is private, restricted, or has been removed by its owner. "
                            "Facebook requires you to be logged into an authorized account to view it."
                        )
                        logger.warning(f"Post {post_id} is unavailable or private: {status_message}")
                    else:
                        status_message = "No high-resolution images were found in this post."
                except Exception:
                    status_message = "No high-resolution images were found in this post."

            result = ScrapeResult(
                post_id=post_id,
                canonical_url=canonical_url,
                original_url=url,
                items=final_items,
                total_discovered=len(final_items),
                metadata=metadata,
                is_private_or_deleted=is_private_or_deleted,
                status_message=status_message,
            )
            return result

        finally:
            await page.close()

    async def _dismiss_modals_and_overlays(self, page: Page) -> None:
        """Dismiss cookie consent modals cleanly without closing post containers."""
        # Check cookie consent buttons
        for selector in COOKIE_CONSENT_SELECTORS:
            try:
                locator = page.locator(selector).first
                if await locator.is_visible(timeout=300):
                    logger.debug(f"Clicking cookie banner button: {selector}")
                    await locator.click(timeout=600)
                    await asyncio.sleep(0.3)
                    break
            except Exception:
                pass

        # Disable pointer events on floating login prompts/backdrops so they do not block interactions or close the post
        try:
            await page.evaluate(
                """
                () => {
                    const prompts = document.querySelectorAll('div[data-nosnippet], div#login_popup, div[role="banner"]');
                    prompts.forEach(el => {
                        if (el.querySelector('input[type="password"]') || (el.innerText && el.innerText.includes('See more on Facebook'))) {
                            el.style.pointerEvents = 'none';
                        }
                    });
                    document.body.style.overflow = 'auto';
                    document.documentElement.style.overflow = 'auto';
                }
                """
            )
        except Exception:
            pass

    async def _extract_from_dom_images(self, page: Page) -> List[MediaItem]:
        """Extract high-resolution images directly from the main post feed DOM."""
        items: List[MediaItem] = []
        seen: Set[str] = set()

        try:
            img_elements = await page.evaluate(
                """
                () => {
                    const results = [];
                    const imgs = document.querySelectorAll('img');
                    for (const img of imgs) {
                        const nw = img.naturalWidth || 0;
                        const nh = img.naturalHeight || 0;
                        const rw = img.width || 0;
                        const rh = img.height || 0;
                        
                        // Keep images that are substantial in size or have srcset
                        if (nw >= 150 || nh >= 150 || rw >= 150 || rh >= 150 || img.srcset) {
                            results.push({
                                src: img.src || '',
                                srcset: img.srcset || '',
                                width: nw || rw,
                                height: nh || rh
                            });
                        }
                    }
                    return results;
                }
                """
            )

            for img in img_elements:
                best_url = None
                if img.get("srcset"):
                    best_url = parse_srcset_largest(img["srcset"])
                if not best_url and img.get("src"):
                    best_url = img["src"]

                if best_url:
                    cleaned = clean_cdn_url(best_url)
                    if is_valid_cdn_image_url(cleaned) and cleaned not in seen:
                        seen.add(cleaned)
                        items.append(
                            MediaItem(
                                url=cleaned,
                                width=int(img.get("width", 0)) or None,
                                height=int(img.get("height", 0)) or None,
                            )
                        )
        except Exception as e:
            logger.debug(f"DOM extraction skipped: {e}")

        return items

    async def _extract_via_media_set(self, page: Page) -> List[MediaItem]:
        """Extract full album photos if post links to a media set (e.g., set=pcb.123 or set=a.123)."""
        items: List[MediaItem] = []
        seen: Set[str] = set()

        try:
            # Check for any album set identifier on the current page (prioritize set=pcb. for post batch)
            set_id = await page.evaluate(
                """
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="set="]')).map(a => a.href);
                    for (const l of links) {
                        try {
                            const u = new URL(l);
                            const s = u.searchParams.get('set');
                            if (s && s.startsWith('pcb.')) {
                                return s;
                            }
                        } catch (e) {}
                    }
                    for (const l of links) {
                        try {
                            const u = new URL(l);
                            const s = u.searchParams.get('set');
                            if (s && s.startsWith('a.')) {
                                return s;
                            }
                        } catch (e) {}
                    }
                    return null;
                }
                """
            )

            if not set_id:
                return items

            set_url = f"https://www.facebook.com/media/set/?set={set_id}"
            logger.debug(f"Discovered album media set: {set_url}. Navigating to album grid...")

            try:
                await page.goto(set_url, wait_until="domcontentloaded", timeout=25000)
                await asyncio.sleep(1.5)
                await self._dismiss_modals_and_overlays(page)

                # Scroll quickly to collect initial photos in grid
                last_count = 0
                unchanged_count = 0

                for scroll_idx in range(6):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                    await asyncio.sleep(0.5)

                    album_imgs = await page.evaluate(
                        """
                        () => {
                            return Array.from(document.querySelectorAll('img')).map(i => ({
                                src: i.src || '',
                                srcset: i.srcset || '',
                                w: i.naturalWidth || i.width || 0,
                                h: i.naturalHeight || i.height || 0
                            })).filter(i => (i.src.includes('fbcdn.net') || i.srcset.includes('fbcdn.net')) && (i.w > 150 || i.h > 150));
                        }
                        """
                    )

                    for img in album_imgs:
                        best_u = None
                        if img.get("srcset"):
                            best_u = parse_srcset_largest(img["srcset"])
                        if not best_u and img.get("src"):
                            best_u = img["src"]

                        if best_u:
                            cleaned = clean_cdn_url(best_u)
                            if is_valid_cdn_image_url(cleaned) and cleaned not in seen:
                                seen.add(cleaned)
                                items.append(
                                    MediaItem(
                                        url=cleaned,
                                        width=img.get("w") or None,
                                        height=img.get("h") or None,
                                    )
                                )

                    if len(items) == last_count:
                        unchanged_count += 1
                        if unchanged_count >= 3:
                            break
                    else:
                        unchanged_count = 0
                        last_count = len(items)

                logger.debug(f"Discovered {len(items)} high-res photos from media set grid.")

            except Exception as e:
                logger.debug(f"Media set navigation skipped/error: {e}")

        except Exception as e:
            logger.debug(f"Media set evaluation error: {e}")

        return items

    async def _extract_via_theater_carousel(self, page: Page) -> List[MediaItem]:
        """Traverse the photo viewer carousel to discover all attached album/multi-photo images."""
        items: List[MediaItem] = []

        try:
            # If not already on a photo page, find the first photo permalink link (prioritizing post album links)
            current_page_url = page.url
            if not any(k in current_page_url for k in ("/photo", "fbid=")):
                photo_href = await page.evaluate(
                    """
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href*="/photo/"], a[href*="/photo.php"], a[href*="fbid="]')).map(a => a.href);
                        const pcb = links.find(l => l.includes('set=pcb.'));
                        const album = pcb || links.find(l => l.includes('set=a.')) || links[0];
                        return album || null;
                    }
                    """
                )
                if photo_href:
                    logger.debug(f"Navigating directly to photo viewer: {photo_href}")
                    try:
                        await page.goto(photo_href, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(1.5)
                        await self._dismiss_modals_and_overlays(page)
                    except Exception as e:
                        logger.debug(f"Photo navigation error: {e}")

            # Remove pointer interception from any login overlay
            await page.evaluate(
                """
                () => {
                    document.querySelectorAll('div[role="dialog"]').forEach(d => {
                        const text = d.innerText || '';
                        if (text.includes('Log In') || text.includes('Create new account') || text.includes('Connect with Facebook')) {
                            d.style.pointerEvents = 'none';
                        }
                    });
                }
                """
            )

            seen_keys: Set[str] = set()
            first_seen_key: Optional[str] = None
            consecutive_unresponsive = 0

            # Step through carousel (works for clicked thumbnail or direct photo permalink)
            for step in range(self.config.carousel_max_steps):
                current_img_url = await self._get_theater_image_url(page)
                if current_img_url:
                    cleaned = clean_cdn_url(current_img_url)
                    photo_key = extract_photo_key(cleaned)

                    if photo_key:
                        if first_seen_key is None:
                            first_seen_key = photo_key
                        elif photo_key == first_seen_key and len(items) >= 10:
                            logger.debug(f"Looped back to first photo after {len(items)} items. Album scan complete.")
                            break

                        if photo_key not in seen_keys:
                            seen_keys.add(photo_key)
                            consecutive_unresponsive = 0

                            # Extract photo_id if available in page url
                            current_url = page.url
                            fbid = None
                            if "fbid=" in current_url:
                                fbid = parse_qs(urlparse(current_url).query).get("fbid", [None])[0]

                            items.append(MediaItem(url=cleaned, photo_id=fbid, index=len(items) + 1))
                            if len(items) % 25 == 0 or len(items) <= 5:
                                logger.debug(f"Discovered carousel photo #{len(items)}")
                        else:
                            consecutive_unresponsive += 1
                            if consecutive_unresponsive >= 90:
                                logger.debug("Photo did not advance after 90 attempts. Ending carousel scan.")
                                break
                    else:
                        consecutive_unresponsive += 1
                        if consecutive_unresponsive >= 90:
                            break
                else:
                    consecutive_unresponsive += 1
                    if consecutive_unresponsive >= 90:
                        break

                # Trigger Next click via JavaScript and ArrowRight
                await page.evaluate(
                    """
                    () => {
                        const b = document.querySelector('[aria-label="Next photo"], [aria-label="Next image"], [aria-label="Next"], div[aria-label="Next photo"]');
                        if (b) b.click();
                    }
                    """
                )
                await page.keyboard.press("ArrowRight")
                await asyncio.sleep(0.24)

        except Exception as e:
            logger.debug(f"Theater carousel traversal ended/skipped: {e}")

        return items

    async def _get_theater_image_url(self, page: Page) -> Optional[str]:
        """Extract the currently active photo URL in theater view."""
        try:
            curr_url = await page.evaluate(
                """
                () => {
                    const imgs = Array.from(document.querySelectorAll('img')).filter(i => {
                        const src = i.src || '';
                        return src.includes('fbcdn.net') && (i.naturalWidth > 200 || i.width > 200);
                    });
                    if (imgs.length > 0) {
                        imgs.sort((a,b) => (b.naturalWidth || b.width) - (a.naturalWidth || a.width));
                        return imgs[0].src;
                    }
                    const selectors = [
                        'div[data-visualcompletion="media-vc-image"] img',
                        'img[data-visualcompletion="media-vc-image"]',
                        'div[role="dialog"] img',
                        'div[role="main"] img'
                    ];
                    for (const s of selectors) {
                        const el = document.querySelector(s);
                        if (el && el.src && el.src.includes('fbcdn.net')) return el.src;
                    }
                    return null;
                }
                """
            )
            if curr_url and is_valid_cdn_image_url(curr_url):
                return curr_url
        except Exception:
            pass
        return None

    async def _extract_from_json_scripts(self, page: Page) -> List[MediaItem]:
        """Extract high-resolution image URLs embedded in application/json scripts."""
        items: List[MediaItem] = []
        seen: Set[str] = set()

        try:
            script_contents = await page.evaluate(
                """
                () => {
                    const scripts = document.querySelectorAll('script[type="application/json"]');
                    return Array.from(scripts).map(s => s.textContent || '');
                }
                """
            )

            for raw_json in script_contents:
                if not raw_json or "fbcdn" not in raw_json:
                    continue
                try:
                    data = json.loads(raw_json)
                    extracted = self._find_images_in_json(data)
                    for url, width, height, photo_id in extracted:
                        cleaned = clean_cdn_url(url)
                        if is_valid_cdn_image_url(cleaned) and cleaned not in seen:
                            seen.add(cleaned)
                            items.append(
                                MediaItem(
                                    url=cleaned,
                                    photo_id=photo_id,
                                    width=width,
                                    height=height,
                                )
                            )
                except Exception:
                    pass

                # Fallback: scan regex for fbcdn URLs in raw text
                try:
                    unescaped_json = raw_json.replace("\\/", "/").replace("\\u002526", "&").replace("\\u0026", "&")
                    raw_urls = re.findall(r'https://[^\s"\'\\<>]+fbcdn\.net/[^\s"\'\\<>]+', unescaped_json)
                    for raw_u in raw_urls:
                        cleaned = clean_cdn_url(raw_u)
                        if is_valid_cdn_image_url(cleaned) and cleaned not in seen:
                            seen.add(cleaned)
                            items.append(MediaItem(url=cleaned))
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"JSON script extraction skipped: {e}")

        return items

    def _find_images_in_json(self, obj) -> List[tuple]:
        """Recursively scan JSON tree for Facebook high-res image URIs."""
        results = []

        if isinstance(obj, dict):
            # Check for direct image nodes (uri, url, src)
            for uri_key in ("uri", "url", "src"):
                if uri_key in obj and isinstance(obj[uri_key], str) and "fbcdn.net" in obj[uri_key]:
                    uri = obj[uri_key]
                    width = obj.get("width")
                    height = obj.get("height")
                    photo_id = obj.get("id") or obj.get("fbid")
                    if (width is None or width >= 150) and (height is None or height >= 150):
                        results.append((uri, width, height, photo_id))

            for key, val in obj.items():
                if isinstance(val, (dict, list)):
                    results.extend(self._find_images_in_json(val))

        elif isinstance(obj, list):
            for item in obj:
                results.extend(self._find_images_in_json(item))

        return results
