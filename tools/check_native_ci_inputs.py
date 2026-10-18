#!/usr/bin/env python3
"""Fail closed unless every input for a clean native FPK build is present."""
from pathlib import Path
import hashlib, json, shutil, sys

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".runtime/native-input-cache"
lock = json.loads((ROOT / "docs/NATIVE_INPUTS.lock.json").read_text())
missing = []

def verify_file(entry, kind):
    p = CACHE / entry["file"]
    if not p.is_file():
        missing.append(f"{kind}: {p}")
        return
    expected = entry.get("sha256")
    if not expected:
        missing.append(f"{kind} has no SHA-256 lock: {entry['file']}")
        return
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    if digest != expected:
        missing.append(f"{kind} hash mismatch: {entry['file']} ({digest} != {expected})")

for entry in lock.get("source_inputs", []):
    verify_file(entry, "locked source input")
for entry in lock.get("runtime_apk_inputs", []):
    verify_file(entry, "runtime APK")

fnpack = lock.get("fnpack")
if not fnpack:
    missing.append("official hash-locked fnpack: lock has no fnpack entry")
else:
    verify_file({"file": fnpack["path"], "sha256": fnpack.get("sha256")}, "fnpack") if fnpack["path"].startswith(".runtime/") else None
    tool = ROOT / fnpack["path"]
    if not tool.is_file():
        missing.append(f"official hash-locked fnpack: {tool}")
    if not fnpack.get("accepted_for_ci", False):
        missing.append(f"official hash-locked fnpack is not accepted for CI: {fnpack['path']}")
    elif not fnpack.get("sha256"):
        missing.append(f"official hash-locked fnpack has no SHA-256 lock: {tool}")
    elif hashlib.sha256(tool.read_bytes()).hexdigest() != fnpack["sha256"]:
        missing.append(f"official hash-locked fnpack hash mismatch: {tool}")

for path, label in [
    (ROOT / ".runtime/native-toolchain", "complete compiler/toolchain"),
    (ROOT / ".runtime/native-runtime", "complete musl/Qt/runtime closure"),
    (ROOT / ".runtime/native-apkbuild", "Alpine APKBUILD/patch closure"),
]:
    if not path.is_dir() or not any(path.iterdir()):
        missing.append(f"{label}: {path}")

if missing:
    print("BLOCKED: clean native x86_64 FPK closure is incomplete", file=sys.stderr)
    print("The workflow refuses to build or publish a placeholder package.", file=sys.stderr)
    for item in missing:
        print(f"- {item}", file=sys.stderr)
    raise SystemExit(2)
print("PASS: complete native FPK closure is present")
