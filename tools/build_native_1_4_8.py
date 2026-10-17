"""Build immutable 1.4.8 formal local package and independent source bundle."""
from pathlib import Path
import hashlib, io, json, os, shutil, subprocess, tarfile, tempfile
R = Path(__file__).resolve().parents[1]


def strip_debug(path: Path) -> None:
    """Remove non-loadable DWARF/debug sections from a release ELF."""
    tool = shutil.which("strip")
    if not tool:
        raise RuntimeError("strip is required for release builds")
    subprocess.run([tool, "--strip-debug", str(path)], check=True)

REL = R / "release"
base = REL / "fnos-qbittorrent-native-1.4.7-x86_64.fpk"
out = REL / "fnos-qbittorrent-native-1.4.8-x86_64.fpk"
source_out = REL / "native-1.4.8-source-bundle.tar.gz"
stage = R / ".runtime/package148"
work = R / ".runtime/source148"
for p in (out, source_out, out.with_suffix(".fpk.sha256"), stage, work, R / ".runtime/gateway148-native", R / ".runtime/build148", R / "evidence/native-package-audit-1.4.8.json"):
    assert not p.exists(), f"immutable output/work already exists: {p}"
assert base.is_file()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
# Capture all pre-existing release files before creating any new artifact.
prior_hashes = R / ".runtime/strip148-prior-hashes.json"
assert not prior_hashes.exists(), f"immutable baseline already exists: {prior_hashes}"
prior_hashes.write_text(json.dumps({str(p.relative_to(R)): sha(p) for p in REL.iterdir() if p.is_file()}, indent=2) + "\n")
# Source bundle is independent and retains the previous complete compliance source set.
source_root = REL / "native-1.1.4-sources"
assert source_root.is_dir(), "complete source material missing"
shutil.copytree(source_root, work / "complete-source")
current = work / "application-source"
current.mkdir()
subprocess.run(["npm", "run", "build"], cwd=R, env=dict(os.environ, VITE_NATIVE="1"), check=True)
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
    "bundle_version": "1.4.8",
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
# Build package from immutable 1.4.7 bytes, then remove only non-runtime source-header/component bundles.
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
(lic / "LICENSE-SOURCES.md").write_text(f'''# Source and license delivery for native 1.4.8\n\nThis FPK is a runtime package. Complete corresponding source, APKBUILD/patch provenance, source hashes, and full license/NOTICE materials are in `{source_out.name}` with SHA-256 `{source_hash}`.\n\nFor GPL/LGPL components, the source bundle is delivered with this version. If this FPK is redistributed separately, it MUST be accompanied by that exact bundle or a written offer that meets the applicable license and remains valid for the recipient. Do not infer that URLs alone satisfy source delivery.\n\nThe FPK retains runtime-needed license texts, full NOTICE, this source manifest, and the distribution warning. Large source-header/component notice trees are intentionally outside the FPK and are retained in the source bundle.\n''')
(lic / "RELEASE-NOTES.md").write_text('''# 飞牛 PT 下载 1.4.8\n\n仅包体优化：最终 staging 的 qB/gateway/native-control 执行 strip --strip-debug；Go gateway 同时使用 -ldflags "-s -w"。不保证 RSS 下降，不改变产品功能。\n\n正式命名的本地 x86_64 构建：原生 qBittorrent 5.2.4，PT 优先；DHT、PeX、LSD、UPnP 关闭。包含保种、限速、分享率、标签/分类与 MoviePilot 入口。\n\n边界：这是本地构建包；未完成真实 NAS 安装/升级、物理手机、路径映射及完整外部发行合规验收。完整源码与本包配套交付，见 SOURCE-MANIFEST.json。\n''')
(lic / "DO-NOT-DISTRIBUTE.txt").write_text(f"Local build boundary: not NAS/physical-phone/external-release-compliance accepted. Accompany with {source_out.name} (SHA256 {source_hash}) or a legally valid written-source offer.\n")
# Version and checksum metadata.
m = stage / "manifest"
def release_line(l):
    key = l.split("=", 1)[0].strip()
    if key == "version":
        return "version               = 1.4.8"
    if key == "display_name":
        return "display_name          = 飞牛 PT 下载"
    if key == "desc":
        return "desc                  = 原生 x86_64 qBittorrent 5.2.4，PT 优先；DHT/PeX/LSD/UPnP 关闭；支持保种、限速、分享率、标签分类与 MoviePilot 入口。"
    if key == "changelog":
        return "changelog             = 1.4.8 strip 包体优化，不保证 RSS 下降；真实 NAS、物理手机与完整外部发行合规仍待验收。"
    return l
m.write_text("\n".join(release_line(l) for l in m.read_text().splitlines() if not l.startswith("checksum")) + "\n")
subprocess.run(["npm", "run", "build"], cwd=R, env=dict(os.environ, VITE_NATIVE="1"), check=True)
for scope in ["public", "private"]:
    p = stage / "app/webui" / scope
    shutil.rmtree(p)
    shutil.copytree(R / "dist", p)
    for f in p.rglob("*.js"):
        f.write_text(f.read_text().replace("/app/fnos-qbittorrent", "/app/fnos-qbittorrent-native"))
sources = R / ".runtime/gateway148-native"; sources.mkdir()
for f in (R / "gateway").glob("*.go"):
    if not f.name.endswith("_test.go"):
        (sources / f.name).write_text(f.read_text().replace("/app/fnos-qbittorrent", "/app/fnos-qbittorrent-native"))
subprocess.run(["go", "build", "-trimpath", "-ldflags", "-s -w", "-o", str(stage / "app/bin/gateway"), *map(str, sources.glob("*.go"))], env=dict(os.environ, GO111MODULE="off", CGO_ENABLED="0"), check=True)
# Capture inherited ELF sections before touching the final staging binaries.
strip_report = []
for relative in ["app/runtime/usr/bin/qbittorrent-nox", "app/bin/gateway", "app/bin/native-control"]:
    binary = stage / relative
    before = subprocess.check_output(["readelf", "-SW", str(binary)], text=True)
    before_size = binary.stat().st_size
    before_hash = sha(binary)
    strip_debug(binary)
    after = subprocess.check_output(["readelf", "-SW", str(binary)], text=True)
    assert ".debug_info" not in after and ".zdebug_info" not in after
    strip_report.append(dict(path=relative, before_bytes=before_size, after_bytes=binary.stat().st_size,
                             before_sha256=before_hash, after_sha256=sha(binary), before_sections=before, after_sections=after))
(R / "evidence/strip-1.4.8.json").write_text(json.dumps(strip_report, indent=2) + "\n")
assert not (stage / "app/licenses/component-notices").exists()
assert not (stage / "app/licenses/source-headers").exists()
for p in [stage / "app/runtime", stage / "app/bin", stage / "app/webui/public", stage / "app/webui/private", stage / "app/ui/config", stage / "manifest", lic / "NOTICE.md", lic / "LICENSE-SOURCES.md", lic / "SOURCE-MANIFEST.json", lic / "RELEASE-NOTES.md"]:
    assert p.exists(), p
build = R / ".runtime/build148"; build.mkdir()
subprocess.run([str(R / "tools/fnpack"), "build", "--directory", str(stage)], cwd=build, check=True)
made = build / "fnos-qbittorrent-native.fpk"; assert made.is_file()
shutil.copyfile(made, out)
(out.with_suffix(".fpk.sha256")).write_text(sha(out) + "  " + out.name + "\n")
report = {"version":"1.4.8", "status":"LOCAL_BUILD_WITH_PLATFORM_BOUNDARY", "fpk":str(out), "fpk_sha256":sha(out), "source_bundle":str(source_out), "source_bundle_sha256":source_hash, "slim_removed":["app/licenses/component-notices","app/licenses/source-headers"], "strip_report":"evidence/strip-1.4.8.json", "rss_reduction_claimed":False, "prior_artifacts_unchanged":True, "nas_verified":False, "gaps":["MoviePilot/Docker/qB real connector/browser acceptance matrix", "PT/labels/409 packaged regression", "NAS/physical phone acceptance"]}
(R / "evidence/native-package-audit-1.4.8.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(report, indent=2, ensure_ascii=False))
