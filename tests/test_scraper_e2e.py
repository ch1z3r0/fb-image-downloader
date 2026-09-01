"""Integration tests for Playwright Facebook Scraper using local test pages."""

import pytest
from fb_downloader.config import ScraperConfig
from fb_downloader.scraper import FacebookScraper


@pytest.mark.asyncio
async def test_scraper_extracts_json_and_dom_images(tmp_path):
    # Create a mock Facebook post HTML page
    html_content = """<!DOCTYPE html>
    <html>
    <head><title>Facebook Post Mock</title></head>
    <body>
        <!-- Cookie banner -->
        <div data-cookiebanner="accept_button">
            <button>Allow all cookies</button>
        </div>

        <!-- Post container -->
        <div role="feed">
            <div role="article" data-pagelet="FeedUnit_0">
                <h1>Mock Post Title</h1>
                <p>Post caption description</p>

                <!-- Photo Grid -->
                <div class="photo-grid">
                    <img
                        src="https://scontent.xx.fbcdn.net/v/t39.30808-6/image_low.jpg"
                        srcset="https://scontent.xx.fbcdn.net/v/t39.30808-6/image_low.jpg 500w, https://scontent.xx.fbcdn.net/v/t39.30808-6/image_high.jpg 2048w"
                        style="width: 800px; height: 600px;"
                    />
                </div>
            </div>
        </div>

        <!-- Embedded Relay JSON Script -->
        <script type="application/json">
        {
            "require": [
                {
                    "data": {
                        "viewer": {
                            "actor": {
                                "id": "1000",
                                "name": "Test User"
                            }
                        },
                        "feedback": {
                            "photo_image": {
                                "uri": "https://scontent.xx.fbcdn.net/v/t39.30808-6/photo_relay_original.jpg?_nc_cat=100&ccb=1-7",
                                "width": 2048,
                                "height": 1536,
                                "id": "9988776655"
                            }
                        }
                    }
                }
            ]
        }
        </script>
    </body>
    </html>
    """

    mock_html_file = tmp_path / "mock_post.html"
    mock_html_file.write_text(html_content, encoding="utf-8")
    file_url = f"file://{mock_html_file.resolve()}"

    config = ScraperConfig(navigation_timeout_ms=5000, page_timeout_ms=5000)
    scraper = FacebookScraper(config=config, headless=True)

    async with scraper:
        # We invoke scrape_post with the file_url
        page = await scraper._context.new_page()
        try:
            await page.goto(file_url)
            # Test modal dismissal
            await scraper._dismiss_modals_and_overlays(page)

            # Test JSON script extraction
            json_items = await scraper._extract_from_json_scripts(page)
            assert len(json_items) >= 1
            assert any("photo_relay_original.jpg" in itm.url for itm in json_items)
            relay_item = next(itm for itm in json_items if "photo_relay_original.jpg" in itm.url)
            assert relay_item.width == 2048
            assert relay_item.height == 1536
            assert relay_item.photo_id == "9988776655"

            # Test DOM srcset extraction
            dom_items = await scraper._extract_from_dom_images(page)
            assert len(dom_items) >= 1
            assert any("image_high.jpg" in itm.url for itm in dom_items)
        finally:
            await page.close()
