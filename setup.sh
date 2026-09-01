#!/usr/bin/env bash
# ============================================================
#  Facebook Image Downloader — One-Command Setup (Mac / Linux)
# ============================================================
set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
RESET='\033[0m'

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${CYAN}║   🚀 Facebook Image Downloader — Setup Script    ║${RESET}"
echo -e "${CYAN}╚══════════════════════════════════════════════════╝${RESET}"
echo ""

# ---------- Check Python ----------
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}❌ Python 3 is not installed.${RESET}"
    echo "   Please install Python 3.9+ from https://www.python.org/downloads/"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${RESET}"

# ---------- Create virtual environment ----------
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚙️  Creating virtual environment...${RESET}"
    python3 -m venv .venv
fi

# ---------- Activate venv ----------
source .venv/bin/activate
echo -e "${GREEN}✅ Virtual environment activated${RESET}"

# ---------- Install dependencies ----------
echo -e "${YELLOW}📦 Installing Python dependencies...${RESET}"
pip install --upgrade pip -q
pip install -e . -q
pip install fastapi uvicorn pytest pytest-asyncio anyio httpx -q

# ---------- Install Playwright browsers ----------
echo -e "${YELLOW}🌐 Installing Playwright Chromium browser...${RESET}"
python -m playwright install chromium --with-deps 2>/dev/null || \
python -m playwright install chromium

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${RESET}"
echo -e "${GREEN}║        ✅ Setup complete! Ready to run.          ║${RESET}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${RESET}"
echo ""
echo -e "  ${CYAN}Launch the Web UI:${RESET}"
echo -e "  ${YELLOW}  source .venv/bin/activate && python main.py --ui${RESET}"
echo ""
echo -e "  ${CYAN}Or open from any device on your Wi-Fi:${RESET}"
echo -e "  ${YELLOW}  source .venv/bin/activate && python main.py --ui${RESET}"
echo -e "  ${YELLOW}  Then open http://<your-ip>:8000 on another device${RESET}"
echo ""
echo -e "  ${CYAN}Enable HTTPS (for folder selection on other devices):${RESET}"
echo -e "  ${YELLOW}  python main.py --ui --ssl${RESET}"
echo ""
