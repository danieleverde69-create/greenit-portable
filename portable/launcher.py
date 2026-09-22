#!/usr/bin/env python3
"""Avvia Green IT in modalita' web locale."""
from __future__ import annotations

import os
import platform
import shutil
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "gestionale-it-local"
# La cartella dati e' condivisa da tutti i launcher presenti sull'SSD.
DATA = ROOT / "data"
WEB_PORT = int(os.environ.get("GREENIT_WEB_PORT", "3000"))
API_PORT = int(os.environ.get("GREENIT_API_PORT", "8174"))


def bundled(name: str) -> Path | None:
    system = platform.system().lower()
    machine = platform.machine().lower()
    candidates = [ROOT / "runtime" / f"{system}-{machine}" / name, ROOT / "runtime" / system / name]
    if system == "windows":
        candidates = [p.with_suffix(".exe") for p in candidates] + candidates
    for candidate in candidates:
        if candidate.exists():
            return candidate
    found = shutil.which(name)
    return Path(found) if found else None


def wait_for_port(port: int, timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as sock:
            sock.settimeout(0.25)
            try:
                sock.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.2)
    return False


def main() -> int:
    service = bundled("greenit-service")
    python = bundled("python") or bundled("python3")
    node = bundled("node")
    if service is None and python is None:
        print("Runtime Python non trovato: aggiungerlo in runtime/<piattaforma>/.", file=sys.stderr)
        return 2
    if node is None:
        print("Runtime Node non trovato: aggiungerlo in runtime/<piattaforma>/.", file=sys.stderr)
        return 2
    DATA.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update({"GREENIT_DATA_DIR": str(DATA), "PORT": str(WEB_PORT), "HOST": "127.0.0.1"})
    processes: list[subprocess.Popen[bytes]] = []
    try:
        api_command = [str(service)] if service else [str(python), str(APP / "local_service.py")]
        processes.append(subprocess.Popen(api_command, cwd=APP, env=env))
        processes.append(subprocess.Popen([str(node), str(APP / "node_modules" / "wrangler" / "bin" / "wrangler.js"), "dev", "--config", "dist/server/wrangler.json", "--port", str(WEB_PORT)], cwd=APP, env=env))
        if not wait_for_port(API_PORT) or not wait_for_port(WEB_PORT):
            print("Impossibile avviare i servizi locali.", file=sys.stderr)
            return 1
        # Il frontend usa il contratto CORS gia' configurato per localhost.
        print(f"Green IT pronto: http://localhost:{WEB_PORT}")
        webbrowser.open(f"http://localhost:{WEB_PORT}")
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return next((p.returncode or 1 for p in processes if p.returncode), 0)
    except KeyboardInterrupt:
        return 0
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
