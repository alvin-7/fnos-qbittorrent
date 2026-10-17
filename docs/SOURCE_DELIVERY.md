# Corresponding source and artifact delivery

## Preserved historical 1.4.0 material

Local `release/fnos-qbittorrent-native-1.4.0-x86_64.fpk` is paired with
`release/native-1.4.0-source-bundle.tar.gz` and the separately retained
`release/native-1.4.0-verification-overlay.tar.gz`. Do not overwrite these
immutable artifacts, regenerate their hashes to conceal changes, or equate this
working-tree cleanup with their original contents.

The FPK's `app/licenses/SOURCE-MANIFEST.json`, `LICENSE-SOURCES.md` and full NOTICE
bind it to source delivery. Retained bundles include upstream source, notices,
source headers, recipes/patches and application source available at build time.
Post-freeze harness corrections are separate overlays. Verify all actual
SHA256 values before delivery; source links alone do not close corresponding-source
obligations. No hash or completeness certification is fabricated by this document.

## Why archives are not in Git

Runtime binaries, source archives, staging outputs and raw evidence are ignored,
not deleted. GitHub source upload is not binary/source-bundle distribution. Any
future binary release must separately deliver exact matching source and notices,
and obtain a license/compliance review. Do not promise a written offer unless the
copyright holder/distributor actually undertakes a legally sufficient offer.

## Rebuild limits

`tools/build_native_1_4_0.py` depends on the old 1.3.9 FPK and retained
`release/native-1.1.4-sources`; it is an incremental historical assembly recipe.
Other historical scripts source-build selected qB/libtorrent/Qt components but do
not establish complete offline toolchain closure. An empty public checkout cannot
currently reproduce the whole native FPK. This is a documented release blocker,
not a reason to copy arbitrary local archives or private paths into Git.

For a future clean reproducible build, inventory exact runtime file ownership,
pinned upstream/APK inputs, compiler/Qt ABI, recipes and patches, verify downloaded
hashes, and test the resulting loader/TLS/API/real private transfer/restart and
packaged iframe. Keep binary provenance and license completion distinct from NAS
and physical-phone acceptance. Original repository work is licensed GPL-3.0-or-later, Copyright (C) 2026 alvin-7. This license does not relicense third-party components; their exact notices, source and applicable obligations remain separate and mandatory.

## Clean checkout application build (verified; not a full native FPK)

Run `python3 tools/build_checkout.py` in a fresh source tree. It performs npm ci,
native-mode UI build and prefix transformation, linux/amd64 gateway/native-control
compilation, Go race/vet and six JS contracts. Output `.runtime/checkout-build`
must not already exist. It uses no historical FPK, staging or source archive.
An independently copied upload-only tree passed this path; it is application build
proof, not offline reproducibility, a runtime/FPK build or NAS acceptance.

`docs/NATIVE_INPUTS.lock.json` records exact upstream qB/libtorrent/Boost URL,
SHA256, size and license, plus retained Alpine recipe revisions and selected APK
hashes. `python3 tools/fetch_native_inputs.py` downloads only those three source
inputs to `.runtime/native-input-cache` with mandatory TLS/hash verification;
`--verify-only --cache <directory>` verifies retained cache. Downloaded archives
are large (sizes in the lock), ignored, never executed/extracted by this tool;
retain their original license texts when redistributing. No fresh large download
was needed here: all three retained cache archives passed SHA256. This lock is
explicitly partial: it does not pretend selected APKs describe the entire runtime.

**Full native FPK remains BLOCKED.** Exact clean compiler/dev APK closure and Qt
private ABI bootstrap, complete runtime file ownership/TLS/CA assembly, legally
sufficient complete matching source and independently acquired/hash-locked fnpack
are not supplied/verified. Old source-build shell scripts assume a prepared
container; old incremental packagers still require old FPKs. Do not run them as
an empty-checkout promise. No new FPK was generated and no historical artifacts
were deleted or modified.
