# Automated GitHub Releases

`.github/workflows/release.yml` runs only when a `v*` tag is pushed. It checks out that immutable tag, builds the UI and Go application, downloads the hash-locked public source inputs, then fails closed unless the complete native x86_64 qBittorrent 5.2.4 / musl / Qt / compiler / APK / `fnpack` closure is present in the checkout or is supplied by an explicit, hash-verified CI input.

A successful run must build a real FPK, audit its contents, calculate SHA256, and run the offline package smoke test. The Release contains exactly the FPK and its `.sha256` file. Source is retained in Git; source and checkout-validation archives are never uploaded. The upload step refuses to overwrite an existing same-name asset, so reruns with the same tag fail rather than replacing immutable release bytes.

## Current clean-build assessment

This checkout was audited on 2026-10-18. The three public source archives in the lock were downloaded to a temporary cache and their SHA-256 values matched. The locally available Docker image is `ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1` with local config digest `sha256:dd9d91f629c25ea0b7758d3b618ac93c8b254e7b42a09b7f9f9c9b21828f1ba0`; Docker reports no registry RepoDigest, and a fresh GHCR pull could not be performed from this environment. It is therefore not accepted as a public locked CI input.

`docs/NATIVE_INPUTS.lock.json` remains explicitly partial. It does not provide the complete compiler/dev APK closure, Qt private ABI bootstrap, complete musl/Qt runtime assembly and ownership/source closure, or a hash-locked official `fnpack`. The historical `build_native_1_4_8.py` and `build_native_1_4_1.py` require local prior FPK/source material and are not clean-checkout builds. CI therefore stops at `check_native_ci_inputs.py` and publishes no FPK rather than downloading an arbitrary runtime or fabricating one. The checker also verifies every cached input hash and rejects an absent or unlocked `fnpack`.

No successful native build/audit/smoke result is claimed. The minimum next step is to publish a verifiable OCI digest (or public source-built image recipe and all layer/source hashes), add the complete toolchain/APKBUILD/Qt-private/runtime closure and official `fnpack` provenance to the lock, then replace the historical builder with a clean-checkout assembler and run it in that pinned environment. The existing `v1.4.8` tag is immutable; this change does not move or rebuild it. A new `v*` tag created from a commit containing a complete closure is required for an automatic release.
