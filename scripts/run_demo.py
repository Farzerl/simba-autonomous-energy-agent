from __future__ import annotations

import argparse
import importlib.util
import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def fail(message: str, code: int = 1) -> None:
    print(f"SIMBA launcher: {message}", file=sys.stderr)
    raise SystemExit(code)


def require_runtime() -> None:
    if sys.version_info < (3, 10):
        fail("Python 3.10 or newer is required for the lightweight application.")
    missing = [name for name in ("fastapi", "pydantic", "uvicorn") if importlib.util.find_spec(name) is None]
    if missing:
        fail(
            "missing Python packages: "
            + ", ".join(missing)
            + ". On Ubuntu run ./setup_ubuntu.sh, then retry."
        )
    required = [
        ROOT / "src" / "api" / "app_server.py",
        ROOT / "src" / "agent" / "service.py",
        ROOT / "config" / "autonomous_agent.json",
        ROOT / "data" / "simulation" / "scenarios.json",
        ROOT / "dashboard" / "index.html",
        ROOT / "dashboard" / "static" / "i18n.js",
    ]
    absent = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if absent:
        fail("copied project is incomplete; missing " + ", ".join(absent))


def port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.5)
        return probe.connect_ex((host, port)) != 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline SIMBA Autonomous Energy Operations Agent.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    require_runtime()
    if not port_available(args.host, args.port):
        fail(f"port {args.port} is already in use; close the existing SIMBA instance or pass --port PORT")

    os.chdir(ROOT)
    os.environ.setdefault("SIMBA_DEMO_MODE", "1")
    os.environ.setdefault("SIMBA_AGENT_PROVIDER", "mock")
    os.environ["SIMBA_CONTROL_MODE"] = "simulation"
    os.environ["SIMBA_CONTROL_ALLOW_LIVE"] = "0"
    url = f"http://{args.host}:{args.port}/?tab=agent"
    print("SIMBA Autonomous Energy Operations Agent")
    print("  mode: software-in-the-loop")
    print("  live electrical control: disabled")
    print(f"  local interface: {url}")
    print("Press Ctrl+C to stop.")

    if not args.no_browser:
        threading.Timer(1.4, lambda: webbrowser.open(url)).start()

    import uvicorn

    uvicorn.run(
        "src.api.app_server:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        log_level="warning",
        access_log=False,
    )


if __name__ == "__main__":
    main()
