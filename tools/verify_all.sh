#!/bin/bash
set -uo pipefail
cd "$(dirname "$0")/.."
# Use the caller's verified Node/npm toolchain from PATH.
mkdir -p evidence
: > evidence/final-exit-codes.tsv
run() { "$@"; code=$?; printf '%s\t%s\n' "$*" "$code" >> evidence/final-exit-codes.tsv; [ "$code" = 0 ] || exit "$code"; }
run python3 tools/build_ui.py
run python3 tools/start_test.py
run npm test
run python3 tools/verify_api.py
run python3 tools/verify_persistence.py
run python3 tools/verify_local_transfer.py
run python3 tools/verify_package.py
run python3 tools/build_package.py
run python3 tools/verify_packaged_runtime.py
run python3 tools/audit_artifact.py
run npm audit --omit=dev --registry=https://registry.npmjs.org --json
