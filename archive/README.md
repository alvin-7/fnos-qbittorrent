# Historical material index (no files moved)

This is a logical archive. Historical version-specific scripts remain in `tools/`
because 1.4.0 build/regression code imports or text-transforms older paths. See
`tools/README.md`. No wrappers or symlinks mask moved inputs.

Local-only archives preserved unchanged and excluded from Git:
- `release/`: every historical FPK/source bundle/checksum/verification overlay.
- `native-package/`, `fnos-qbittorrent/`: old native/Docker staging trees, runtime,
  licenses and binary inputs. Their manifests are not current release metadata.
- `evidence/`: raw historical logs/reports/screenshots (potential private data).
- `.runtime/`: generated fixtures, private credentials, build staging/cache and
  the recoverable pre-cleanup backup at `github-readiness-backup/`.
- historical `docs/RELEASE*`, `docs/native-*`, `docs/platform/` and named live
  investigation/acceptance notes: retained on disk, excluded until sanitized.

Recovery: originals and SHA256 are in `.runtime/github-readiness-backup/originals/`
and `original-manifest.json`. Restore only explicitly changed paths from that
backup after reviewing the manifest; newly added docs/config can be removed
individually. Do not restore the whole tree over concurrent work. There has been
no mass deletion, history rewrite, git initialization or package regeneration.
