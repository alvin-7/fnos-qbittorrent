# Directory contract investigation — current source, not an installer

## Confirmed versus field-unknown

- Confirmed reproducible lifecycle bug: native/control.go rejected any `:` in TRIM_DATA_SHARE_PATHS. Official environment contract explicitly specifies colon-separated resource shares. Added regression first, observed panic, then fixed. Chinese/spaces remain literal. Fresh initialization uses first resource root only; upgrades retain existing qB DefaultSavePath; no probes/writes into secondary roots.
- Confirmed diagnostic bug: provider collapsed missing token, 401, 403, 404, business invalid params and schema failure into AUTH_SOURCE_UNAVAILABLE; service further discarded errors. Fixed reason propagation through roots/checked/browse and write guard. API raw msg/body/token never returned. Positive app grants wholly filtered by ACL/filesystem are AUTH_ROOTS_INACCESSIBLE, not zero authorization. Genuine successful paths:[] returns NO_APP_GRANTS.
- Official `trim.file.getSharedAccessibleFolders` is **administrator grants to this application**, not a user-visible shared-folder list. Current fixed appName/request/path schema matches the published contract. `checkUserACL` is a separate current-user requirement explicitly prescribed before returning content. Do not remove this boundary merely because the package account has ACL. No evidence yet establishes which NAS stage is failing.
- TRIM_DATA_SHARE_PATHS means resource-created shares; TRIM_DATA_ACCESSIBLE_PATHS means user-authorized accessible paths. Both colon-delimited. Neither is a proven continuously refreshed shared-grants snapshot. No environment/OS-readability/prefs fallback was added.
- Launch scripts exec native-control without env filtering; native-control launches gateway with append(os.Environ(),...). No source evidence of environment loss. Real NAS gateway environment remains unknown.
- User screenshot confirms qb-native has 4 permission rows (default plus 3), two same display names and one cross-volume personal directory. Display names are not absolute paths. Existing code deduplicates canonical paths, not names. Contract regression covers 4 paths with 2 same basenames, Chinese/spaces, simulated multiple-volume path layout. This is not actual separate mounts.

## Scroll root cause and fix

Picker was mounted inside a scrollable parent modal and backdrop-filter overlay, with no page scroll lock. Moved picker to document.body portal (avoid containing block/scroll clipping), introduced reference-counted fixed-body lock preserving styles and scroll position, integrated Settings and visibility-aware AddTask. Directory list retains min-height:0/overflow:auto with touch-action pan-y, overscroll containment and momentum scrolling; header/footer do not shrink. No blanket touchmove cancellation.

## Real local verification

- `GO111MODULE=off go test -race ./gateway ./native -count=1`: PASS.
- Official HTTP contract provider tests invoke actual production fnosDirectoryProvider with test-only redirected transport and real local directories. Four roots returned; all validate; unauthorized readable sibling rejected. UID in ACL request asserted 1000. This is **not qb-native NAS UID proof**.
- `VITE_NATIVE=1 npm run build`: PASS.
- `tools/verify_directory_scroll_current.mjs` against current built dist: PASS 1440 and 390 widths, real Chromium wheel and CDP touch gestures; list scrolls, background remains locked, bottom-edge wheel does not propagate, header/footer remain in viewport, nested settings lock survives picker close, final close restores scrollY=320. Safe API route fixtures, not NAS/qB proof. Evidence: evidence/directory-scroll-current.json.
- Dev-server attempt failed ENOSPC watcher limit from historical .runtime trees. Used a read-only Python static dist server instead; no system limits altered.
- Safe probe local execution returns GATEWAY_PROCESS_NOT_UNIQUE, because no unique installed package gateway exists here. This is expected local blocker behavior, not NAS evidence.

## Next field evidence / no blind package

No 1.5.2 FPK built; no git/NAS/credentials/real user tasks touched. Current source changes are not install-ready. Need run `tools/diagnose_directory_contract_safe.py` under installed qb-native account on NAS (owner to choose approved command transport). It reads only the matching package gateway's environment and queries read-only shared-grants API; prints presence/count/type/HTTP/business code, never paths/token/raw messages. It refuses ambiguous process selection or different UID. Return only JSON result. Python availability, package process exe path and same-UID proc visibility require field confirmation.

Outstanding: NAS actual API result/installed scopes/token, resource-share union semantics, current-user ACL versus package account intersection, actual package UID Windows ACL; isolated current native gateway + real qB four-root path readback; immutable package audit/hash once concrete field cause is established. Historical 1.5.1 evidence is not certification of these edits.

## Official references consulted

- https://developer.fnnas.com/docs/core-concepts/environment-variables
- https://developer.fnnas.com/docs/core-concepts/resource/
- https://developer.fnnas.com/api/calling/
- https://developer.fnnas.com/api/authorization/shared-access/
- https://developer.fnnas.com/api/authorization/file-acl/
- https://developer.fnnas.com/api/error-codes/
