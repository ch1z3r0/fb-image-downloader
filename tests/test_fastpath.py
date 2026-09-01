"""Unit tests for the async FastPathExtractor."""

import pytest
from unittest.mock import AsyncMock, patch

from fb_downloader.fastpath import FastPathExtractor
from fb_downloader.models import MediaItem


SAMPLE_HTML_WITH_OG = """
<!DOCTYPE html>
<html>
<head>
    <meta property="og:image" content="https://scontent.xx.fbcdn.net/v/t39.30808-6/123456789_n.jpg?stp=dst-jpg&oh=abcdef&oe=123456" />
    <meta property="og:image:url" content="https://scontent.xx.fbcdn.net/v/t39.30808-6/123456789_n.jpg?stp=dst-jpg&oh=abcdef&oe=123456" />
</head>
<body>
    <h1>Sample Post</h1>
</body>
</html>
"""

SAMPLE_HTML_WITH_JSON = """
<!DOCTYPE html>
<html>
<head><title>Facebook Post</title></head>
<body>
<script type="application/json" data-sjs>
{
    "require": [
        ["RelayPrefetchedStreamCache", "next", [], [
            "feedback_123",
            {
                "data": {
                    "node": {
                        "attachments": [
                            {
                                "media": {
                                    "__typename": "Photo",
                                    "id": "10160163935296772",
                                    "image": {
                                        "uri": "https:\\/\\/scontent.xx.fbcdn.net\\/v\\/t39.30808-6\\/987654321_n.jpg?stp=dst-jpg\\u0026_nc_cat=100",
                                        "width": 2048,
                                        "height": 1536
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        ]]
    ]
}
</script>
</body>
</html>
"""

SAMPLE_HTML_WITH_LOW_RES = """
<!DOCTYPE html>
<html>
<body>
    <!-- Avatar (low-res) -->
    <meta property="og:image" content="https://scontent.xx.fbcdn.net/v/t39.30808-1/p50x50/avatar123_n.jpg" />
    <!-- Small icon -->
    <img src="https://static.xx.fbcdn.net/rsrc.php/v3/y8/r/icon.png" />
    <!-- Full resolution photo -->
    <script>
        var payload = {"full_res_image": {"uri": "https:\\/\\/scontent-iad3-2.xx.fbcdn.net\\/v\\/t39.30808-6\\/444555666_full.jpg?stp=dst-jpg\\u0026oh=xyz"}};
    </script>
</body>
</html>
"""

SAMPLE_HTML_PRIVATE = """
<!DOCTYPE html>
<html>
<body>
    <div>This content isn't available right now. When this happens, it's usually because the owner only shared it with a small group of people, changed who can see it or it's been deleted.</div>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_fastpath_opengraph_extraction():
    extractor = FastPathExtractor()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML_WITH_OG
        mock_get.return_value = mock_resp

        result = await extractor.extract("https://www.facebook.com/NASA/posts/10160163935296772")
        assert result is not None
        assert not result.is_private_or_deleted
        assert len(result.items) == 1
        assert "123456789_n.jpg" in result.items[0].url
        assert result.post_id == "10160163935296772"


@pytest.mark.asyncio
async def test_fastpath_relay_json_extraction():
    extractor = FastPathExtractor()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML_WITH_JSON
        mock_get.return_value = mock_resp

        result = await extractor.extract("https://www.facebook.com/NASA/posts/10160163935296772")
        assert result is not None
        assert len(result.items) == 1
        item = result.items[0]
        assert "987654321_n.jpg" in item.url
        assert item.width == 2048
        assert item.height == 1536


@pytest.mark.asyncio
async def test_fastpath_low_res_filtering():
    extractor = FastPathExtractor()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML_WITH_LOW_RES
        mock_get.return_value = mock_resp

        result = await extractor.extract("https://www.facebook.com/NASA/posts/10160163935296772")
        assert result is not None
        assert len(result.items) == 1
        assert "444555666_full.jpg" in result.items[0].url
        assert "avatar123_n.jpg" not in result.items[0].url


@pytest.mark.asyncio
async def test_fastpath_private_or_deleted_detection():
    extractor = FastPathExtractor()
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.text = SAMPLE_HTML_PRIVATE
        mock_get.return_value = mock_resp

        result = await extractor.extract("https://www.facebook.com/private/posts/999999999")
        assert result is not None
        assert result.is_private_or_deleted is True
        assert len(result.items) == 0
        assert "private" in (result.status_message or "").lower()
