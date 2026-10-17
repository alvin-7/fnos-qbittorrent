#!/usr/bin/env python3
"""Audit a native FPK without modifying it."""
from pathlib import Path
import hashlib, io, sys, tarfile, tempfile

p = Path(sys.argv[1])
if not p.is_file() or p.suffix != ".fpk":
    raise SystemExit("expected an existing .fpk")
with tarfile.open(p) as outer, tempfile.TemporaryDirectory() as td:
    outer.extractall(td, filter="data")
    root = Path(td)
    app_tgz = root / "app.tgz"
    manifest = root / "manifest"
    if not app_tgz.is_file() or not manifest.is_file():
        raise SystemExit("invalid FPK: app.tgz or manifest missing")
    with tarfile.open(app_tgz) as app:
        names = set(app.getnames())
    required = {"bin/gateway", "bin/native-control", "runtime/usr/bin/qbittorrent-nox", "webui/public", "licenses/NOTICE.md"}
    missing = sorted(x for x in required if not any(n == x or n.startswith(x + "/") for n in names))
    if missing:
        raise SystemExit("FPK audit missing: " + ", ".join(missing))
print(f"PASS FPK audit: {p} sha256={hashlib.sha256(p.read_bytes()).hexdigest()}")
