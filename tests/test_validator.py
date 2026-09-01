"""Tests for environment validation."""

from fb_downloader.validator import validate_environment


def test_validate_environment(tmp_path):
    is_valid, msg = validate_environment(str(tmp_path))
    assert is_valid is True
    assert "successful" in msg.lower()
