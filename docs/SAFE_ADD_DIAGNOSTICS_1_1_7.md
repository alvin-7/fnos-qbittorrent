# Native 1.1.7 — asynchronous add diagnosis local closure

## Exact 1.1.6 finding
The classifier extracted from the immutable 1.1.6 FPK DOES recognize the exact `Failed to add torrent` / expected-bencoded-value / `[bdecode:4]` signature as category `非torrent`, code `INVALID_TORRENT`. It does not preserve numeric code 4, use the requested fixed explanation, poll diagnostics beyond the one read after five task polls, color that diagnostic as an error, or retain it when AddTask is unmounted. The reason for 1.1.7 is this behavioral gap, not an unsupported-signature claim. Evidence: `evidence/classifier116-exact.txt` (test run against extracted original Go source).

## Changes
- `gateway/diagnostics.go`: exact expected-value plus `[bdecode:4]` maps to fixed `category=INVALID_TORRENT`, `code=BENCODE_PARSE_ERROR`, integer `numeric_code=4`. Only the fixed explanation is returned, never Source/Reason strings or URLs. Other unknowns remain unknown. URL removal precedes classification; nested and encoded URL canaries tested.
- `src/AddTask.tsx`, `src/main.tsx`: retain one AddTask instance while its dialog is hidden. A serial observation loop checks tasks and diagnostic cursor until a new hash, background error, expired/unavailable cursor, or a 45-second observation deadline. An in-flight API request itself has the existing 20-second timeout, so wall-clock completion can exceed 45 seconds on an unresponsive backend. No diagnostic interval exists, no repeated mount timers, no business POST replay. Closing/reopening during observation retains the same request and eventual result. Recent safe feedback is page-memory only and is lost on full reload. Manual refresh does one observation pass, not a new add or new cursor; expired diagnostic state retains the error. Existing qB native preflight/session/CSRF code unchanged.
- HTTP202/accepted is not task success. New hashes prove task appearance, not completed download. Time-correlated log errors explicitly remain association-unconfirmed.

## Real packaged UI / gateway / qB result
`python tools/verify_diagnostics117_real.py` PASS. Uses exact package117 gateway, WebUI and runtime with isolated local profile, a test-only port mapping bridge (qB Host/CSRF remain enabled), iframe, and controlled local HTTP source. No NAS or real signed URL.

Real HTML response delayed 7 seconds (beyond old five polls) and real JSON response both produced zero new hashes and the following visible red alert (`rgb(184, 58, 65)`):

> INVALID_TORRENT [BENCODE_PARSE_ERROR] 返回内容不是有效种子（bdecode:4），可能为站点错误响应，具体响应未知（该时段后台错误，关联未确认）

UI also displayed: `后台出现错误，未观察到新增 hash；不能确认添加或下载成功。未自动重试。`
Gateway response contained only safe integer timestamp/category/code/numeric_code/fixed message/association. Browser evidence captures these responses, not raw logs. Closing during delayed HTML, reopening, settled reopening and manual refresh passed. Five UI add requests produced exactly five business POSTs. URL query preserved; normal URL and file each added one hash and settled to `queuedDL` (not paused); magnet with pause added one hash in `stoppedDL`. No transfer-completion claim.

Endpoint absent token/wrong token/valid token/source query/POST = 403/403/200/400/405. `/api/v2/app/version` from exact packaged runtime = `v5.2.4`.
Evidence: `evidence/diagnostics117-browser.json`.

## Other gates
- `GO111MODULE=off go test -race ./gateway ./native`: PASS (native authentication/session, diagnostics, privacy, origin tests).
- Native production build/typecheck: PASS.
- `node tools/verify_diagnostics117_state.mjs`: PASS on native build. Explicit mock202; diagnostic first arrives on seventh read; red failure/reopen retention; expiry preserves old error; no-log observation settles after 45593 ms; no diagnostic reads after settlement; two user submissions = two POSTs. Evidence: `evidence/diagnostics117-state.json`.
- Existing `tests/business-diagnostics.spec.ts`: 5/5 PASS on non-native production build. Fixed test locator to wait for the relevant status instead of strict-matching two temporary status elements. Early Vite/dev-server runs failed when server disappeared; stable in-process Python static server run passed. This was harness failure, not treated as product acceptance.
- First real Go run expected old `非torrent` category and failed after structured category intentionally changed; corrected test expectation. First browser assertion rejected the negative phrase `不能确认添加或下载成功`; corrected test to require that negative phrase. Final harness also uses unique fixture hashes for repeatability. FPK remains immutable; final test-only corrections are in the separately hashed final overlay.

## Immutable artifacts / audit
- FPK `release/fnos-qbittorrent-native-1.1.7-x86_64.fpk`
  SHA256 `3898f8fde04e0db753c4aad8785188d4682587cbf3885987a8e367dc04a226af`
- Final source/test overlay `release/native-1.1.7-diagnostics-final-source-overlay.tar.gz`
  SHA256 `42b30e8418a98f9892ccb679a2b201c4ca26206e2d92fe4137ec7cf995e36d2c`
- Initial embedded/adjacent UI overlay predates final test-only corrections; use final overlay for reproduction. Production Go/TS in final overlay match the exact packaged sources.
- Audits `evidence/native-package-audit-1.1.7.json`, `evidence/native-package-final-audit-1.1.7.json`: manifest 1.1.7; all 25,038 original non-UI/non-gateway files, complete original license tree and runtime preserved byte-for-byte. Gateway rebuilt. Preserve adjacent corresponding runtime source `release/native-1.1.4-sources.tar.gz` and its SHA256 sidecar; original source/rebuild/legal limitations remain unchanged, no new legal-completeness warranty.

No NAS operation, real user URL, Git commit or publishing. Real fnOS installation/upgrade, socket ACL and NAS incident causality remain unverified.
