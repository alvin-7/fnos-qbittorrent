#!/usr/bin/env python3
"""Minimal offline FPK smoke check; never contacts NAS or uses credentials."""
from pathlib import Path
import sys, tarfile, tempfile

p = Path(sys.argv[1])
with tarfile.open(p) as outer, tempfile.TemporaryDirectory() as td:
    outer.extractall(td, filter="data")
    root = Path(td)
    with tarfile.open(root / "app.tgz") as app:
        names = set(app.getnames())
    if not any(n.endswith("/runtime/usr/bin/qbittorrent-nox") or n == "runtime/usr/bin/qbittorrent-nox" for n in names):
        raise SystemExit("smoke failed: qBittorrent runtime absent")
    if not any(n.endswith("/bin/gateway") or n == "bin/gateway" for n in names):
        raise SystemExit("smoke failed: gateway absent")
print("PASS offline FPK smoke: qBittorrent runtime and gateway are packaged")
