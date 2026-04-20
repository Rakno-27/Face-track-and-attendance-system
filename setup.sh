#!/usr/bin/env bash
# ─────────────────────────────────────────────
#  FaceTrack Easy Setup — Linux / macOS
#  Usage: bash setup.sh
# ─────────────────────────────────────────────
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   FaceTrack — Easy Setup & Launch   ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Python check ──
if ! command -v python3 &>/dev/null; then
  echo "❌ Python 3 not found. Install Python 3.9+ first."
  exit 1
fi
echo "✅ Python $(python3 --version 2>&1 | cut -d' ' -f2) found"

# ── System deps hint ──
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
  echo ""
  echo "⚠️  If this is your first run, install system deps:"
  echo "    sudo apt-get install -y cmake build-essential libopenblas-dev liblapack-dev libx11-dev"
  echo ""
fi

# ── Venv ──
if [ ! -d "venv" ]; then
  echo "🔧 Creating virtual environment…"
  python3 -m venv venv
fi

source venv/bin/activate

# ── Install deps ──
echo "📦 Installing dependencies…"
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "🚀 Starting FaceTrack…"
echo "   Open: http://localhost:5000"
echo ""
python app.py
