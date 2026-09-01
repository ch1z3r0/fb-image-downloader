"""Automated environment and dependency validator."""

import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Tuple

logger = logging.getLogger("fb_downloader.validator")


def validate_environment(output_dir: str = "./downloads") -> Tuple[bool, str]:
    """Validate system requirements, Playwright browser installation, and disk permissions.

    Returns:
        Tuple of (is_valid, message)
    """
    # 1. Python version check
    if sys.version_info < (3, 8):
        return False, f"Python 3.8+ required. Detected Python {sys.version_info.major}.{sys.version_info.minor}"

    # 2. Output directory write permission check
    try:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        test_file = out_path / f".write_test_{os.getpid()}"
        test_file.write_text("ok")
        test_file.unlink()
    except Exception as e:
        return False, f"Output directory is not writable ({output_dir}): {e}"

    # 3. Playwright module check
    try:
        import playwright  # noqa: F401
    except ImportError:
        return False, "Playwright Python package is not installed. Run: pip install playwright"

    # 4. Playwright Chromium browser binary check
    try:
        # Check standard cache paths for chromium
        cache_paths = [
            Path.home() / "Library" / "Caches" / "ms-playwright",
            Path.home() / ".cache" / "ms-playwright",
            Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright",
        ]
        has_chromium = any(
            p.exists() and any(p.glob("chromium*")) for p in cache_paths
        )

        if not has_chromium:
            # Fallback to direct playwright API check if no event loop running
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if not loop:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    executable_path = p.chromium.executable_path
                    if not executable_path or not Path(executable_path).exists():
                        return (
                            False,
                            "Playwright Chromium browser binary is not installed.\n"
                            "Please run: playwright install chromium",
                        )
            else:
                return (
                    False,
                    "Playwright Chromium browser binary is not found in standard cache locations.\n"
                    "Please run: playwright install chromium",
                )
    except Exception as e:
        return (
            False,
            f"Failed to verify Playwright Chromium installation: {e}\n"
            "Try running: playwright install chromium",
        )

    return True, "Environment validation successful."


def install_playwright_browsers() -> bool:
    """Attempt to install Playwright Chromium automatically."""
    try:
        logger.info("Installing Playwright Chromium browser...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info("Chromium installed successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to auto-install Playwright browsers: {e}")
        return False


def get_local_ip() -> str:
    """Detect the host machine's primary local network IP address (e.g. 192.168.x.x)."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Connect to public DNS IP to identify the active network interface without sending data
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"
