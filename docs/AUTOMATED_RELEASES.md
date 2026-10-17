# Automated GitHub Releases

`.github/workflows/release.yml` is triggered by a push of a tag matching `v*` (or manually for an existing tag). It checks out that immutable tag, runs `tools/build_checkout.py`, and creates or reuses the corresponding GitHub Release.

The workflow publishes only CI-produced, uniquely named assets:

- `fnos-qbittorrent-<version>-source.tar.gz`
- `fnos-qbittorrent-<version>-checkout-validation.tar.gz`
- `SHA256SUMS`
- `release-notes.md` is used when a Release is first created

Reruns never use `--clobber` for release assets. If an asset already exists, the workflow downloads it and compares its SHA256 with the artifact produced in the rerun; a mismatch fails rather than replacing an immutable asset.

## FPK boundary

A clean checkout can build and test the UI, Go gateway, and native-control. It cannot currently rebuild a complete native qBittorrent FPK from Git alone: the complete compiler/runtime/APK closure, Qt private ABI bootstrap, complete runtime assembly, matching source delivery, and verified `fnpack` input are not all present and locked. `docs/NATIVE_INPUTS.lock.json` is explicitly partial. Therefore CI does **not** download an arbitrary runtime or upload an FPK by inference. Release notes explicitly state that an FPK must be manually supplied and SHA256-verified if one is later distributed.

A real FPK path may be added only after a reproducible build recipe has all inputs locked and the CI job actually builds, packages, and verifies the result. Until then, do not add an FPK upload step or treat a local ignored `release/` file as a CI artifact.

## Existing releases and tags

`v1.4.8` was created before this workflow existed on `main` (`v1.4.8` points to `175f821`; the workflow was added later at `ea47dc8`). Its existing Release is not retroactively triggered by this change. Do not move or recreate that tag. A future `v*` tag created from a commit containing this workflow will trigger the automated Release flow; the tag must be created and pushed by the project owner when ready.
