# ─────────────────────────────────────────────────────
#  Facebook Image Downloader — Docker Image
# ─────────────────────────────────────────────────────
FROM python:3.11-slim

# Install system dependencies for Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libpango-1.0-0 libpangocairo-1.0-0 \
    fonts-liberation libappindicator3-1 \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python deps first (layer caching)
COPY requirements.txt pyproject.toml ./
COPY fb_downloader/__init__.py fb_downloader/
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir fastapi uvicorn httpx anyio

# Install Playwright Chromium
RUN python -m playwright install chromium --with-deps

# Copy full project
COPY . .

EXPOSE 8000

# Default: launch the Web UI on all interfaces
CMD ["python", "main.py", "--ui", "--host", "0.0.0.0", "--port", "8000"]
