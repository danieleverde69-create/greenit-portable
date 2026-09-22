#!/usr/bin/env python3
"""Assembla un pacchetto Green IT portable per una piattaforma."""
from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "gestionale-it-local"
RUNTIME = ROOT / "runtime"
OUT = ROOT / "release"


def copy_tree(source: Path, target: Path) -> None:
    if not source.exists():
        raise FileNotFoundError(source)
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".wrangler", ".git", "__pycache__"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("platform", help="windows-x64, darwin-x64, darwin-arm64 o linux-x64")
    args = parser.parse_args()
    runtime = RUNTIME / args.platform
    service_names = ("greenit-service", "greenit-service.exe", "python", "python.exe")
    if not any((runtime / name).exists() for name in service_names):
        print(f"Servizio/runtime Python mancante: {runtime}", file=sys.stderr)
        return 2
    if not (runtime / "node").exists() and not (runtime / "node.exe").exists():
        print(f"Runtime Node mancante: {runtime}", file=sys.stderr)
        return 2
    if not (APP / "node_modules").exists():
        print("node_modules mancante: eseguire npm ci prima del packaging", file=sys.stderr)
        return 2
    name = f"GreenIT-{args.platform}"
    destination = OUT / name
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    copy_tree(APP, destination / "gestionale-it-local")
    copy_tree(runtime, destination / "runtime" / args.platform)
    copy_tree(ROOT / "portable", destination / "portable")
    # Una sola cartella dati alla radice: i pacchetti dei diversi OS possono
    # essere estratti nella stessa directory GreenIT sull'SSD.
    source_data = APP / "data"
    target_data = destination / "data"
    if source_data.exists():
        copy_tree(source_data, target_data)
    shutil.rmtree(destination / "gestionale-it-local" / "data", ignore_errors=True)
    target_data.mkdir(parents=True, exist_ok=True)
    archive = OUT / f"{name}.zip"
    OUT.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for item in destination.rglob("*"):
            if item.is_file():
                bundle.write(item, Path("GreenIT") / item.relative_to(destination))
    print(f"Creato: {archive}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
