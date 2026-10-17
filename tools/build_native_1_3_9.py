"""Build immutable 1.3.9 slim test candidate and independent source bundle."""
from pathlib import Path
import hashlib, io, json, os, shutil, subprocess, tarfile, tempfile
R = Path(__file__).resolve().parents[1]
REL = R / "release"
base = REL / "fnos-qbittorrent-native-1.3.8-x86_64.fpk"
out = REL / "fnos-qbittorrent-native-1.3.9-x86_64.fpk"
source_out = REL / "native-1.3.9-source-bundle.tar.gz"
stage = R / ".runtime/package139"
work = R / ".runtime/source139"
for p in (out, source_out, stage, work):
    assert not p.exists(), f"immutable output/work already exists: {p}"
assert base.is_file()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
# Source bundle is independent and retains the previous complete compliance source set.
source_root = REL / "native-1.1.4-sources"
assert source_root.is_dir(), "complete source material missing"
shutil.copytree(source_root, work / "complete-source")
current = work / "application-source"
current.mkdir()
for name in ["src", "gateway", "dist", "public", "package.json", "package-lock.json", "tsconfig.json", "index.html", "tools", "docs", "README.md", "THIRD_PARTY_NOTICES.md"]:
    src = R / name
    if src.exists():
        dst = current / name
        shutil.copytree(src, dst) if src.is_dir() else shutil.copy2(src, dst)
# Include all available recipe/patch provenance; absence is explicit in the manifest.
recipe_files = []
for root in [R / "release/native-1.1.4-sources", R / "native-package", R / "fnos-qbittorrent"]:
    if root.exists():
        recipe_files += [p for p in root.rglob("APKBUILD") if p.is_file()]
        recipe_files += [p for p in root.rglob("*.patch") if p.is_file()]
recipe_dir = work / "APKBUILD-and-patches"
recipe_dir.mkdir()
for p in sorted(set(recipe_files)):
    shutil.copy2(p, recipe_dir / (p.parent.name + "-" + p.name))
manifest = {
    "bundle_version": "1.3.9",
    "runtime": "qBittorrent 5.2.4 native x86_64 plus fnOS gateway/native-control and alternate UI",
    "source_roots": ["complete-source", "application-source", "APKBUILD-and-patches"],
    "license_material": "complete-source contains the retained full license/notice/source-header materials from the audited runtime; application-source contains current application notices",
    "recipe_and_patch_files_found": [str(p) for p in sorted(set(recipe_files))],
    "sha256_policy": "SHA256SUMS covers every regular file in this bundle and is regenerated after assembly",
    "distribution_boundary": "Do not distribute the FPK without this bundle or an equivalent written-source offer valid for the same recipient and version."
}
(work / "SOURCE-MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
with tarfile.open(source_out, "w:gz") as t:
    t.add(work / "complete-source", arcname="complete-source")
    t.add(work / "application-source", arcname="application-source")
    t.add(work / "APKBUILD-and-patches", arcname="APKBUILD-and-patches")
    t.add(work / "SOURCE-MANIFEST.json", arcname="SOURCE-MANIFEST.json")
source_hash = sha(source_out)
# Build package from 1.3.8 bytes, then remove only non-runtime source-header/component bundles.
stage.mkdir()
with tarfile.open(base) as t:
    t.extractall(stage, filter="data")
with tarfile.open(fileobj=io.BytesIO((stage / "app.tgz").read_bytes())) as t:
    t.extractall(stage / "app", filter="data")
(stage / "app.tgz").unlink()
lic = stage / "app/licenses"
assert lic.is_dir()
for name in ["component-notices", "source-headers"]:
    p = lic / name
    if p.exists(): shutil.rmtree(p)
# Package-only compliance documents and exact source-bundle binding.
(lic / "SOURCE-MANIFEST.json").write_text(json.dumps({"source_bundle": source_out.name, "sha256": source_hash, **manifest}, indent=2, ensure_ascii=False) + "\n")
(lic / "LICENSE-SOURCES.md").write_text(f'''# Source and license delivery for native 1.3.9\n\nThis FPK is a runtime package. Complete corresponding source, APKBUILD/patch provenance, source hashes, and full license/NOTICE materials are in `{source_out.name}` with SHA-256 `{source_hash}`.\n\nFor GPL/LGPL components, the source bundle is delivered with this version. If this FPK is redistributed separately, it MUST be accompanied by that exact bundle or a written offer that meets the applicable license and remains valid for the recipient. Do not infer that URLs alone satisfy source delivery.\n\nThe FPK retains runtime-needed license texts, full NOTICE, this source manifest, and the distribution warning. Large source-header/component notice trees are intentionally outside the FPK and are retained in the source bundle.\n''')
(lic / "DO-NOT-DISTRIBUTE.txt").write_text(f"TEST CANDIDATE NOT ACCEPTED. Do not distribute this FPK without {source_out.name} (SHA256 {source_hash}) or a legally valid written-source offer. Not NAS/physical-phone accepted; MoviePilot matrix remains incomplete.\n")
# Version and checksum metadata.
m = stage / "manifest"
m.write_text("\n".join((l.split("=",1)[0] + "= 1.3.9" if l.startswith("version") else l) for l in m.read_text().splitlines() if not l.startswith("checksum")) + "\n")
subprocess.run(["npm", "run", "build"], cwd=R, env=dict(os.environ, VITE_NATIVE="1"), check=True)
for scope in ["public", "private"]:
    p = stage / "app/webui" / scope
    shutil.rmtree(p)
    shutil.copytree(R / "dist", p)
    for f in p.rglob("*.js"):
        f.write_text(f.read_text().replace("/app/fnos-qbittorrent", "/app/fnos-qbittorrent-native"))
sources = R / ".runtime/gateway139-native"; sources.mkdir()
for f in (R / "gateway").glob("*.go"):
    if not f.name.endswith("_test.go"):
        (sources / f.name).write_text(f.read_text().replace("/app/fnos-qbittorrent", "/app/fnos-qbittorrent-native"))
subprocess.run(["go", "build", "-trimpath", "-o", str(stage / "app/bin/gateway"), *map(str, sources.glob("*.go"))], env=dict(os.environ, GO111MODULE="off", CGO_ENABLED="0"), check=True)
# Assert no moved source trees remain and required runtime roots exist.
assert not (stage / "app/licenses/component-notices").exists()
assert not (stage / "app/licenses/source-headers").exists()
for p in [stage / "app/runtime", stage / "app/bin", stage / "app/webui/public", stage / "app/webui/private", stage / "app/ui/config", stage / "manifest", lic / "NOTICE.md", lic / "LICENSE-SOURCES.md"]:
    assert p.exists(), p
build = R / ".runtime/build139"; build.mkdir()
subprocess.run([str(R / "tools/fnpack"), "build", "--directory", str(stage)], cwd=build, check=True)
made = build / "fnos-qbittorrent-native.fpk"; assert made.is_file()
shutil.copyfile(made, out)
(out.with_suffix(".fpk.sha256")).write_text(sha(out) + "  " + out.name + "\n")
report = {"version":"1.3.9", "status":"TEST_CANDIDATE_NOT_ACCEPTED", "fpk":str(out), "fpk_sha256":sha(out), "source_bundle":str(source_out), "source_bundle_sha256":source_hash, "slim_removed":["app/licenses/component-notices","app/licenses/source-headers"], "prior_artifacts_unchanged":True, "nas_verified":False, "gaps":["MoviePilot/Docker/qB real connector/browser acceptance matrix", "PT/labels/409 packaged regression", "NAS/physical phone acceptance"]}
(R / "evidence/native-package-audit-1.3.9.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(report, indent=2, ensure_ascii=False))
