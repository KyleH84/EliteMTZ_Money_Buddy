#!/bin/bash
set -euo pipefail

# Resolve to this script's directory so renaming the outer folder doesn't matter
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Clear potentially noisy login shell messages
export BASH_SILENCE_DEPRECATION_WARNING=1

# 1) Find python3
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif [ -x /usr/bin/python3 ]; then
    PYTHON=/usr/bin/python3
else
    echo "❌ python3 not found. Install Xcode CLT (xcode-select --install) or Homebrew Python."
    echo "   After install, double-click this script again."
    exit 1
fi

# 2) Create/Use venv (no version hardcoding)
VENV_DIR="$SCRIPT_DIR/.venv311"
if [ ! -d "$VENV_DIR" ]; then
    echo "📦 Creating virtual environment at $VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# 3) Ensure pip is present and up-to-date
python -m ensurepip -U >/dev/null 2>&1 || true
python -m pip install --upgrade pip >/dev/null 2>&1 || true

# 4) Install requirements (if any)
REQ="$SCRIPT_DIR/Extras/requirements.txt"
if [ -f "$REQ" ]; then
    echo "⬇️  Installing dependencies from Extras/requirements.txt (first run may take a bit)"
    python -m pip install -r "$REQ"
fi

# 5) Launch the app (no version in path)
echo "🚀 Launching AstroLotto (Streamlit)"
exec python -m streamlit run programs/app_main.py
