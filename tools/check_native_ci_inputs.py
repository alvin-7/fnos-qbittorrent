#!/usr/bin/env python3
"""Fail closed unless every input for a clean native FPK build is present."""
from pathlib import Path
import json, shutil, sys

ROOT = Path(__file__).resolve().parents[1]
lock = json.loads((ROOT / "docs/NATIVE_INPUTS.lock.json").read_text())
missing = []
for entry in lock.get("source_inputs", []):
    p = ROOT / ".runtime/native-input-cache" / entry["file"]
    if not p.is_file():
        missing.append(f"locked source input: {p}")
for entry in lock.get("runtime_apk_inputs", []):
    p = ROOT / ".runtime/native-input-cache" / entry["file"]
    if not p.is_file():
        missing.append(f"runtime APK: {p}")
for path, label in [
    (ROOT / "tools/fnpack", "official hash-locked fnpack"),
    (ROOT / ".runtime/native-toolchain", "complete compiler/toolchain"),
    (ROOT / ".runtime/native-runtime", "complete musl/Qt/runtime closure"),
    (ROOT / ".runtime/native-apkbuild", "Alpine APKBUILD/patch closure"),
]:
    if not path.exists():
        missing.append(f"{label}: {path}")

if missing:
    print("BLOCKED: clean native x86_64 FPK closure is incomplete", file=sys.stderr)
    print("The workflow refuses to build or publish a placeholder package.", file=sys.stderr)
    for item in missing:
        print(f"- {item}", file=sys.stderr)
    raise SystemExit(2)
print("PASS: complete native FPK closure is present")
