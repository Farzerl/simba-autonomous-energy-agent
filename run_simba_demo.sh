#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"
export SIMBA_DEMO_MODE=1
export SIMBA_AGENT_PROVIDER=mock
export SIMBA_CONTROL_MODE=simulation
export SIMBA_CONTROL_ALLOW_LIVE=0

if [[ -x "$HERE/.venv/bin/python" ]]; then
  PYTHON="$HERE/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="python3"
else
  echo "SIMBA launcher: Python 3 was not found." >&2
  echo "Run ./setup_ubuntu.sh, then retry." >&2
  exit 1
fi

exec "$PYTHON" "$HERE/scripts/run_demo.py" "$@"
