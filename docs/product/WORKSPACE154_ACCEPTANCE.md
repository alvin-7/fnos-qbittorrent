# 1.5.4 local acceptance matrix

This is a locked-runtime build (1.4.8 FPK runtime reused), NOT a clean native runtime rebuild. No Git commit/push/tag/release or NAS operation was performed. All tasks and credentials used were isolated test fixtures.

| Gate | Result | Evidence / limitation |
|---|---|---|
| Analysis frontend no raw Tracker URL fetch | verified | `Analysis.tsx` calls protected aggregation only; browser counted zero Tracker requests while analysis was open |
| Backend aggregation / privacy | verified | Go `TestAnalysisSafeSites`: safe hostnames only, eligible/running hash sets, per-site/global dedup, TTL expiry; implementation 4 slots and single-flight lock |
| Actual private flag | verified | pinned qB properties `private` (not invented torrents/info.private / is_private) with real private completed fixture |
| Storage | verified | protected POST directories/storage, real Fstatfs total/free/available/used; 4 same-mount roots represented once; revocation and removed-root unknown regression |
| O_PATH | verified | UID 1000, real ancestor 0111, ancestor ReadDir denied, final root enumerable |
| Go race | verified | `GO111MODULE=off go test -race ./gateway ./native` |
| Native UI compilation | verified | native build compiled TypeScript and Vite |
| 1440/390/360 iframe | verified | packaged UI served by real qB 5.2.4, test-only authorized Unix provider; analysis, filter, selection/batch stop readback, add-directory nested locks, detail, settings; no horizontal overflow |
| Rate/share-ratio | verified | packaged iframe changed normal limits and enabled ratio 0.5, saved/readback, disabled and observed qB normalized disabled status at all widths |
| npm regression | partial | initial `npm test` failed because historical 18080/15173 fixtures were absent. Vite serving was unreliable in this environment; static final dist serving subsequently passed all 11 share-ratio Playwright tests. Historical full suite has not passed. |
| MoviePilot client regression | verified subset | exact package gateway, Docker sibling qbittorrent-api==2026.6.0: login/version, category/tag CRUD, private multipart add, malicious-origin and sensitive-route denial, disable closes listener. Full historical acceptance not claimed. |
| FPK/source binding | verified | resource scopes/duplicate effective members audited, 249 app files equal staging, old releases unchanged; `evidence/workspace154-artifact.json` |
| Real NAS / physical phone / platform ACL | blocked / out of scope | local UID/provider simulation is not NAS platform proof |

## Artifacts

- `release/fnos-qbittorrent-native-1.5.4-x86_64.fpk`
- `release/native-1.5.4-source-bundle.tar.gz`
- corresponding `.sha256` files
- `evidence/workspace154-artifact.json`, `workspace154-browser.json`, `workspace154-real.json`, `connector154-real.json`
- packaged iframe analysis/detail PNGs at 1440, 390, 360

Post-build harness corrections/additions and stricter traverse-only assertion are retained in the additive verification overlay; they do not alter the immutable 1.5.4 FPK or source archive. No claim that 1.5.4 is fully accepted/production-ready: full npm suite, exhaustive UI resource-filter/site-return/scroll-position contracts, final production-binary provider-success transport, and broader connector session/restart matrix remain to be exercised. The provider-success test uses a test gateway binary compiled from the same current sources; only the missing-token fail-closed check uses the exact packaged production gateway.
