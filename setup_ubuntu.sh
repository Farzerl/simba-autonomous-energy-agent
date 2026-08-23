#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

WITH_MODEL=0
if [[ "${1:-}" == "--with-model" ]]; then
  WITH_MODEL=1
elif [[ $# -gt 0 ]]; then
  echo "usage: ./setup_ubuntu.sh [--with-model]" >&2
  exit 2
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: Python 3 was not found. Install Python 3.10 or newer." >&2
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
  echo "error: Python 3.10 or newer is required for the SIMBA application." >&2
  echo "note: the separate official ADTC profiler currently requires Python 3.11 or newer." >&2
  exit 1
fi

if ! python3 -m venv --help >/dev/null 2>&1; then
  echo "error: Python venv support is unavailable." >&2
  echo "On Ubuntu 22.04 install it with: sudo apt-get install python3-venv" >&2
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Creating an isolated Python environment..."
  python3 -m venv .venv
fi

echo "Installing the lightweight offline application dependencies..."
".venv/bin/python" -m pip install --upgrade pip
".venv/bin/python" -m pip install -r requirements-ubuntu-agent.txt

if [[ $WITH_MODEL -eq 1 ]]; then
  echo "Downloading the public GGUF used by the separate ADTC model-profile lane..."
  bash download_model.sh
fi

PREFLIGHT_ARGS=(--allow-placeholders)
if [[ ! -f "MANIFEST.sha256" ]]; then
  PREFLIGHT_ARGS+=(--development-tree)
fi
".venv/bin/python" scripts/adtc_preflight.py "${PREFLIGHT_ARGS[@]}"

echo
echo "Setup complete. Start the local demo with:"
echo "  ./run_simba_demo.sh"
echo
echo "The application runs locally after setup. Network access is not used by the demo."
