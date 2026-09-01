# 📸 Facebook Post Image Downloader Pro

> Download **all high-resolution photos** from any Facebook post or album — with a beautiful Web UI, local network sharing, and direct folder selection.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)
![Playwright](https://img.shields.io/badge/Playwright-Chromium-orange?logo=playwright)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-36%20passing-brightgreen)

---

## ✨ Features

- 🖼️ **Download 200+ photos** from a single post with full scroll-based extraction
- 🌐 **Beautiful Web UI** — dark glassmorphism design, gallery view, lightbox
- 📱 **LAN Sharing** — open from your phone, tablet, or another PC on the same Wi-Fi
- 📂 **Folder Selection** — save directly into any folder on your computer
- 🗜️ **Named ZIP Downloads** — type a folder name, get an organized ZIP
- 🔒 **HTTPS mode** — enables native folder picker for other devices on the network
- 🌍 **All image formats** — JPEG, PNG, WebP, AVIF, HEIC, GIF, BMP, TIFF, SVG
- 🔍 **Private post detection** — friendly error when a post is restricted
- 📖 **Tutorial page** — built-in guide on how to get the right Facebook link

---

## 🚀 Quick Start

Choose the method that works best for you:

### Option 1 — One-Command Setup (Recommended)

**Mac / Linux:**
```bash
git clone https://github.com/ch1z3r0/fb-image-downloader.git
cd fb-image-downloader
bash setup.sh
```

Then launch:
```bash
source .venv/bin/activate
python main.py --ui
```

**Windows:**
```
git clone https://github.com/ch1z3r0/fb-image-downloader.git
cd fb-image-downloader
setup.bat
```

Then launch:
```
.venv\Scripts\activate && python main.py --ui
```

Open **http://localhost:8000** in your browser. ✅

---

### Option 2 — Docker (No Python needed)

Requires [Docker Desktop](https://www.docker.com/products/docker-desktop/).

```bash
git clone https://github.com/ch1z3r0/fb-image-downloader.git
cd fb-image-downloader
docker-compose up
```

Open **http://localhost:8000** in your browser. Downloaded photos appear in the `./downloads/` folder.

---

### Option 3 — Manual Setup

```bash
git clone https://github.com/ch1z3r0/fb-image-downloader.git
cd fb-image-downloader

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
pip install fastapi uvicorn httpx anyio

python -m playwright install chromium

python main.py --ui
```

---

## 📖 How to Use

### 1. Get the Right Facebook Link

Click the **📖 How to Get Link** button in the app for a visual guide, or follow these steps:

| Platform | Steps |
|----------|-------|
| **Desktop** | Open the post → Click the timestamp (e.g. "2 hours ago") → Copy the URL from your browser |
| **Mobile** | Open the post → Tap ⋯ (three dots) → **Copy link** |

> ✅ Use the link to the **post** (not a single photo). The app will extract all photos.

### 2. Paste & Scan

Paste the Facebook post URL into the app and click **Scan Post**.

### 3. Select & Download

- Select individual photos or click **Select All**
- Choose how to save:
  - **📂 Save to Selected Folder** — picks a folder on your computer (Chrome/Edge + HTTPS)
  - **📦 Download ZIP** — type a folder name, get an organized ZIP file
  - **🖼️ Download Files** — individual loose files to your Downloads folder
  - **💾 Save to Host Server** — saves to the server machine's disk

---

## 🌐 Local Network (LAN) Sharing

Share access with anyone on the same Wi-Fi — no installation needed on their device.

```bash
python main.py --ui
```

The terminal shows two URLs:
```
🏠 Local Host:    http://localhost:8000
📱 Local Network: http://192.168.x.x:8000  ← share this with others
```

Other devices just open that URL in their browser and can download photos straight to their own device.

### Enable Folder Selection for Other Devices (HTTPS)

Browsers only allow native folder picking over HTTPS. Start with `--ssl` to enable it:

```bash
python main.py --ui --ssl
```

Other devices open `https://192.168.x.x:8000`, click **Accept Risk** once, then **"Save to Selected Folder"** works natively.

---

## ⚙️ CLI Reference

```
Usage: python main.py [OPTIONS] [URL]

Options:
  --ui                Launch the Web UI (default when no URL given)
  --host TEXT         Host to bind to [default: 0.0.0.0]
  --port INTEGER      Port to run on [default: 8000]
  --ssl               Enable HTTPS with self-signed cert (unlocks LAN folder picker)
  --output TEXT       Output directory for CLI downloads
  --headless          Run browser headless (default: True)
  --concurrency INT   Parallel download workers [default: 5]
  --check             Check environment and exit
  --install-browsers  Install Playwright Chromium
  --verbose           Enable debug logging
```

**Examples:**
```bash
# Launch Web UI
python main.py --ui

# Launch on HTTPS for LAN folder picking
python main.py --ui --ssl

# Download from CLI directly
python main.py "https://www.facebook.com/share/p/..." --output ~/Desktop/Photos

# Custom port
python main.py --ui --port 9090
```

---

## 📁 Project Structure

```
fb-image-downloader/
├── fb_downloader/          # Core Python package
│   ├── scraper.py          # Playwright-based Facebook scraper
│   ├── downloader.py       # Concurrent image downloader
│   ├── web_server.py       # FastAPI server + API endpoints
│   ├── cdn_utils.py        # CDN URL parsing & image format detection
│   ├── cli.py              # Typer CLI interface
│   └── models.py           # Pydantic data models
├── web/                    # Frontend
│   ├── index.html          # Main Web UI
│   ├── tutorial.html       # How-to guide
│   ├── js/app.js           # UI logic
│   └── css/style.css       # Glassmorphism dark theme
├── tests/                  # 36 unit tests
├── setup.sh                # Mac/Linux setup
├── setup.bat               # Windows setup
├── Dockerfile              # Docker image
└── docker-compose.yml      # Docker Compose
```

---

## 🔧 Requirements

- **Python 3.9+**
- **Chrome/Chromium** (installed automatically by Playwright)
- **Internet connection** (to access Facebook)
- Facebook posts must be **publicly visible** (or logged-in — not currently supported)

---

## ❓ Troubleshooting

| Problem | Solution |
|---------|----------|
| Only getting 5–10 photos from a large album | Make sure you're using the **post link**, not a single photo link |
| "Post is private or restricted" message | The post is not publicly visible — it requires Facebook login |
| "Save to Selected Folder" button doesn't open picker | Start with `--ssl` flag, or use "Ask where to save" in browser settings |
| Playwright browser not found | Run `python -m playwright install chromium` |
| Port 8000 already in use | Use `--port 9090` (or any free port) |

---

## 📜 License

MIT — free to use, modify, and distribute.

---

## ⭐ Star this repo if it helped you!
