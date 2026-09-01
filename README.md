# Facebook Post Image Downloader Pro

A production-grade Python tool and modern Web UI for scraping and downloading high-resolution photos from Facebook posts, albums, multi-photo grids, and share links using Playwright browser automation and concurrent streaming downloads.

---

## 🌟 Key Features

- **🎨 Modern Glassmorphic Web UI**: Complete single-page dashboard with real-time scraping feedback, interactive photo gallery, multi-select toolbar, fullscreen high-res lightbox, and one-click ZIP export.
- **⚡ Multi-Format URL Resolution**: Supports canonical posts (`facebook.com/.../posts/...`), share links (`fb.com/share/p/...`), photo permalinks (`photo/?fbid=...`), and mobile links.
- **🛡️ Anti-Bot & Modal Bypass**: Automatically dismisses cookie consent dialogs and login modal barriers without requiring account credentials.
- **🖼️ Multi-Photo Grid Expansion**: Clicks into photo thumbnails, opens the Facebook Theater viewer carousel, and walks through multi-photo albums with keyboard navigation (`ArrowRight`).
- **🔍 High-Res CDN Filtering**: Strips out avatars, UI sprites (`rsrc.php`), emojis (`emoji.php`), and tracking beacons. Parses `srcset` descriptors and embedded GraphQL `<script type="application/json">` tags to capture full-size (2048px/1080px) images.
- **🚀 Concurrent Chunked Downloader**: Streams images asynchronously using `httpx.AsyncClient` with connection pooling, retries, and chunked disk writes.
- **📦 Dynamic Content-Type Formatting**: Automatically detects response `Content-Type` headers (`image/jpeg`, `image/png`, `image/webp`) and binary magic bytes to name files cleanly as `photo_001.jpg`, `photo_002.png`, etc.
- **📊 Rich Terminal UI**: Live multi-task progress bars with download speeds, remaining times, and final summary tables.
- **✅ Pre-Flight Environment Validation**: Automatically validates Python version, directory write permissions, and Playwright Chromium installation.

---

## 📦 Installation

```bash
# 1. Clone repository and set up virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Playwright Chromium browser
playwright install chromium
# or run:
python main.py --install-browsers
```

---

## 🌐 Launching the Web UI (Local & Network Access)

Launch the web server and open the interactive dashboard in your browser:

```bash
# Launch Web UI on Local Network (accessible by phones & other PCs on same Wi-Fi)
python main.py --ui

# Or specify a custom port / host
python main.py --ui --port 8080 --host 0.0.0.0
```

When started, the terminal will display both access points:
- **🏠 Local Host**: `http://localhost:8000`
- **📱 Local Network (LAN)**: `http://192.168.x.x:8000` *(Scan or open directly on your mobile device!)*

---

## 💻 CLI Usage

```bash
# Basic download
python main.py "https://www.facebook.com/share/p/123456789/"

# Custom output directory and visible browser
python main.py "https://www.facebook.com/zuck/posts/1011442129999" --output ./my_photos --no-headless

# High concurrency with verbose debug logs
python main.py "https://www.facebook.com/photo/?fbid=1122334455" --concurrency 8 --verbose

# Perform environment health check
python main.py --check-only
```

### Options Reference

| Flag | Shorthand | Type | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `url` | - | `str` | Required / Optional | Facebook post URL or share link |
| `--ui` | - | `flag` | `False` | Launch the interactive Web UI dashboard |
| `--port` | `-p` | `int` | `8000` | Port for Web UI server |
| `--output` | `-o` | `str` | `./downloads/<post_id>/` | Destination directory |
| `--headless / --no-headless` | - | `bool` | `True` | Run Chromium in headless mode |
| `--concurrency` | `-c` | `int` | `5` | Maximum concurrent downloads (1-20) |
| `--verbose` | `-v` | `bool` | `False` | Enable debug logs |
| `--check-env / --no-check-env` | - | `bool` | `True` | Run pre-flight environment checks |
| `--install-browsers` | - | `flag` | - | Auto-install Playwright browser binaries |
| `--check-only` | - | `flag` | - | Run health checks without scraping |

---

## 🏗️ Architecture & Modules

```
downloader/
├── fb_downloader/
│   ├── __init__.py      # Package definition
│   ├── config.py        # Selectors, timeouts, CDN filter regexes
│   ├── models.py        # Pydantic data models (MediaItem, ScrapeResult, DownloadResult)
│   ├── url_utils.py     # URL validation, canonicalization, post ID extraction
│   ├── cdn_utils.py     # Avatar/sprite filtering, srcset parser, MIME resolution
│   ├── scraper.py       # Playwright browser manager, modal bypass, grid & JSON extractor
│   ├── downloader.py    # Async streaming downloader with Rich progress UI
│   ├── validator.py     # Pre-flight environment & Playwright binary validator
│   ├── web_server.py    # FastAPI web backend (REST API & ZIP streaming)
│   └── cli.py           # Typer CLI definition with Rich styling & Web UI launcher
├── web/                 # Modern Frontend Single Page App
│   ├── index.html       # Semantic HTML5 layout
│   ├── css/style.css    # Dark glassmorphic design system
│   └── js/app.js        # Reactive gallery, lightbox, and ZIP exporter
├── tests/               # Pytest automated test suite (32 unit & API tests)
├── main.py              # Application entry point
├── requirements.txt     # Dependency specifications
└── pyproject.toml       # Build configuration and pytest settings
```

---

## 🧪 Running Tests

```bash
# Run all unit, API, and e2e integration tests
pytest -v
```
