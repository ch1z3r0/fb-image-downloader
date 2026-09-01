"""Tests for URL parsing and normalization utilities."""

import pytest
from fb_downloader.url_utils import (
    extract_post_id,
    is_valid_facebook_url,
    normalize_facebook_url,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.facebook.com/zuck/posts/1011442129999", True),
        ("https://facebook.com/share/p/1B6mJ83kLM/", True),
        ("https://m.facebook.com/photo.php?fbid=987654321&set=a.123", True),
        ("https://fb.watch/xyz123/", True),
        ("https://google.com/search?q=facebook", False),
        ("invalid-url", False),
        ("", False),
    ],
)
def test_is_valid_facebook_url(url, expected):
    assert is_valid_facebook_url(url) == expected


@pytest.mark.parametrize(
    "url,expected_id",
    [
        ("https://www.facebook.com/share/p/192837465/", "192837465"),
        ("https://www.facebook.com/zuck/posts/1010101010", "1010101010"),
        ("https://www.facebook.com/permalink.php?story_fbid=778899&id=1000", "778899"),
        ("https://www.facebook.com/photo/?fbid=1122334455&set=pcb.9988", "1122334455"),
        ("https://www.facebook.com/photo.php?fbid=55443322", "55443322"),
        ("https://www.facebook.com/media/set/?set=a.999888777", "999888777"),
    ],
)
def test_extract_post_id(url, expected_id):
    assert extract_post_id(url) == expected_id


def test_normalize_facebook_url():
    raw = "http://m.facebook.com/share/p/12345/?mibextid=wwXIfr"
    canonical, post_id = normalize_facebook_url(raw)
    assert canonical.startswith("https://www.facebook.com/share/p/12345/")
    assert post_id == "12345"
