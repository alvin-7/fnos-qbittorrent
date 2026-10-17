# Automated GitHub Releases

`.github/workflows/release.yml` runs only when a `v*` tag is pushed. It checks out that immutable tag, builds the UI and Go application, downloads the hash-locked public source inputs, then fails closed unless the complete native x86_64 qBittorrent 5.2.4 / musl / Qt / compiler / APK / `fnpack` closure is present in the checkout or is supplied by an explicit, hash-verified CI input.

A successful run must build a real FPK, audit its contents, calculate SHA256, and run the offline package smoke test. The Release contains exactly the FPK and its `.sha256` file. Source is retained in Git; source and checkout-validation archives are never uploaded. The upload step refuses to overwrite an existing same-name asset, so reruns with the same tag fail rather than replacing immutable release bytes.

## Current clean-build assessment

The repository currently locks qBittorrent, libtorrent, Boost, Alpine recipe provenance, and some APK hashes, but `docs/NATIVE_INPUTS.lock.json` explicitly remains partial. It does not provide the complete compiler/dev APK closure, Qt private ABI bootstrap, complete musl/Qt runtime assembly and ownership/source closure, or a hash-locked official `fnpack`. The historical `build_native_1_4_8.py` and `build_native_1_4_1.py` also require local prior FPK/source material and a local `tools/fnpack`; they are not clean-checkout builds. CI therefore stops at `check_native_ci_inputs.py` and publishes no FPK rather than downloading an arbitrary runtime or fabricating one.

When the missing closure is added as reproducible, public, hash-locked CI inputs, the same tag workflow can proceed to the real build. Until then, no FPK claim is made. The existing `v1.4.8` tag points to an earlier commit and is immutable; this change does not move or rebuild it. A new `v*` tag created from a commit containing this workflow is required for an automatic release.
