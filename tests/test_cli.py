"""Tests for CLI commands and arguments."""

import re
from typer.testing import CliRunner
from fb_downloader.cli import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Facebook post" in result.output


def test_cli_check_only():
    result = runner.invoke(app, ["--check-only"])
    assert result.exit_code == 0
    assert "successful" in result.output.lower()


def test_cli_invalid_url():
    result = runner.invoke(app, ["https://google.com/search?q=test"])
    assert result.exit_code == 1
    normalized = re.sub(r"\s+", " ", result.output)
    assert "not recognized as a valid Facebook URL" in normalized


def test_cli_missing_url():
    result = runner.invoke(app, [])
    assert result.exit_code == 1
    assert "Missing Facebook post URL" in result.output
