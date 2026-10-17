# Tool entry points and historical archive policy

## Current source checks (no package creation)

- `npm run build`; `GO111MODULE=off go test -race ./gateway ./native`
- `GO111MODULE=off go vet ./gateway ./native`
- `test_selection140.mjs`, `test_label_batch130.mjs`, `test_labels130.mjs`, `test_connector134_validation.mjs`: focused UI logic/validation contracts.
- `verify_selection140_real.py`: set `SELECTION_PACKAGE=140` explicitly (historical default remains 139).
- `verify_regression140.py`: real PT transfer/scheduler/settings + packaged iframe, controlled invalid-content add diagnostics; uses final `.runtime/package140`.
- `verify_connector140_real.py`: explicit `CONNECTOR_TEST_BIND` required; isolated Docker client using MoviePilot-pinned qbittorrent-api.
- `audit_selection140.py`: compares final FPK/staging/source; requires local archive inputs.

## Historical build/release tools — preserved in place

All `build_native_1_*`, `verify_*119*`/older release-specific scripts, Docker-era
`build_package.py`, `start_test.py`, `verify_all.sh`, source/compliance collectors
and `rebuild_*` are historical compatibility inputs, **not** a default CI pipeline.
Some current 1.4.0 harnesses read older script text and transform paths. Moving them
into archive would break those literal dependencies. They therefore remain at
original paths; the archive is logical, not a destructive filesystem migration.
See `../archive/README.md` and `../docs/GITHUB_READINESS.md`.

Do not run `verify_all.sh` as a public-source readiness gate: it resets Docker
fixtures and builds old FPKs. Never bypass immutable output assertions by deleting
prior packages. `fnpack` is a local binary excluded from Git; obtain the official
tool independently and verify provenance before packaging.
