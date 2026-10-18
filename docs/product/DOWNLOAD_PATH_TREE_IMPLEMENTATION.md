# Download directory picker implementation / local acceptance

Status: **partial local delivery; not NAS accepted and not recommended as installation-ready**. User approved implementation after reviewing the actual OpenDesign exports. Original design and promotional files remain untouched.

## Implemented

- Protected native Unix/admin/origin/CSRF directory routes outside `/api/v2`: roots, single-level browse, validate. Current `trim.file.getSharedAccessibleFolders` plus `trim.file.checkUserACL` are queried for every request and before native add/path writes. No OS-readability, preferences, recent paths or environment snapshot fallback.
- Official contract re-read: https://developer.fnnas.com/api/authorization/shared-access , /api/authorization/file-acl , /api/calling . Fixed appName `fnos-qbittorrent-native`; private Unix platform socket; process TRIM_API_TOKEN; sharedAccess/userAcl scopes in package resource. No NAS platform socket exists locally.
- Native lifecycle inherits environment; it still requires one declared data-share to initialize the existing application. Dynamically authorized additional roots do not alter lifecycle defaults or cause writes/probes across roots. Resource roots absent from the live dynamic response are deliberately unavailable (resource union contract unresolved).
- Package-UID filesystem operations delegated to bounded concurrent killable subprocesses; FD-relative no-follow path traversal; child mount IDs checked; paginated getdents offsets, max 100 directories and 2000 scanned entries/page, expiring opaque server cursors. No recursive walk, file reads, mkdir/move/delete.
- Conservative limitation: **all symlinks are refused**, including within-root links. First-observed root identity is pinned until restart. This is not proof against a mount disappearing before first observation, and NAS mount semantics remain a blocker.
- Desktop tree / mobile full-screen layers plus tree toggle, breadcrumbs, parent, current path, highlight, fixed cancel/confirm, safe-area and 44px controls. Add/default/temp/category-create form integration only fills drafts. Temp enable state is retained as an explicit checkbox.
- Native add/default/temp/category path writes revalidate. Preference path changes with existing tasks and category changes affecting auto-TMM tasks are blocked. MoviePilot retains its previously confirmed transparent business API; private routes and upstream getDirectoryContent are explicitly refused on native and connector paths.

## Verified locally

- `GO111MODULE=off go test -race ./gateway`: PASS after final source edits. Includes real temp directories, 225-child paging, files omitted, unauthorized paths, traversal/symlink refusal, live revocation/source outage, connector GET/POST/encoded directory API isolation and normal transparent API.
- `VITE_NATIVE=1 npm run build`: PASS.
- `tools/verify_directory151_real.py`: PASS. 1440/390 real iframe, formal add/settings entry, choose/cancel/only-fill, invalid pasted path, root error fail-closed, mobile tree toggle, footer44 and no unauthorized name. **fnOS provider/ACL simulated in test-only Go test binary; real directories and qB 5.2.4**. Final packaged production gateway separately returned 503 AUTH_SOURCE_UNAVAILABLE when platform source missing.
- `evidence/directory151-real-readback.json`: protected preferences write/read-back and paused magnet task exact authorized save_path on isolated real qB; UID 1000 local user, **not NAS qb-native UID verification**.
- `evidence/selection151-browser.json`: final 1.5.1 packaged gateway/UI 1440/390 batch force/start/stop, category/tag read-back, selection, partial failure/no replay.
- `evidence/pt151-real-core.json`: real private 4MiB transfer, seeding, queue/force/stop/start, limits persistence, actual near-minute scheduler transitions.
- `evidence/connector151-real.json`: Docker sibling using MoviePilot-pinned qbittorrent-api 2026.6.0, real qB multipart add/category/tag read-back, bad origin, management isolation and disable. First localhost-name interface choice was rejected (409); retested successful on observed concrete local route interface. No production configuration changed.

## Artifact and source binding

- `release/fnos-qbittorrent-native-1.5.1-x86_64.fpk`
- SHA256 `7a1707dfeadbfaeeb42f99c333e252f41a0b64db3e071968eaad10c672f457c1`
- `release/native-1.5.1-source-bundle.tar.gz`
- SHA256 `b72583207ad1c8d32b9662a34bbd9c98d1562c365036117a5182701386df0477`
- `evidence/directory151-artifact.json`: 249 packaged regular-file records audited against staging, historical hashes unchanged, package checksum/source binding. fnpack duplicates `config/resource` members; effective final member and outer resource contain both scopes. Do not interpret its intermediate duplicate as missing scope.
- Build explicitly reuses locked 1.4.8 runtime and retained complete source material; current UI/gateway compiled locally. **Not a clean runtime/compiler closure build**.
- 1.4.9 and 1.5.0 failed audits are retained immutable and stale; never install them. 1.5.0 staging UI was used as disposable pre-final verification surface after its audit failed; its archive was not overwritten. 1.5.1 is the final-source functional artifact. Tests/evidence added after package freeze are bound in a separate verification overlay.

## Open acceptance blockers / deviations

- No real NAS scope/token/API response, shared-resource inclusion semantics, Windows ACL, package UID, dynamic revocation, mount-offline/first-observation protection, physical phone or fnOS entry acceptance. These are **blocked**, not implied by mocked provider success.
- Need adversarial same-path root replacement/offline-before-first-use tests, actual uninterruptible mount syscall kill/reap proof, per-user fairness/rate limit and ACL/revision behavior under live NAS changes. Current four-worker cap does not prove all slow-mount resource budgets.
- No category edit UI added (existing create form reused); no per-layer scroll restoration verification. Initial-path validate selects but does not auto-expand ancestor tree. Full keyboard tree semantics/parent writeability still need review.
- qB auto-TMM/category/default override permutations and direct/browser field duplicates need deeper security acceptance. Raw transparent MoviePilot mutations intentionally retain existing authority; no claim all external-client writes enforce current-user fnOS ACL.
- 1440/390 screenshots taken in a real browser, not OpenDesign; current screenshots capture unselected directory state, not sufficient for long-selected-path visual acceptance.
- Do not tag, publish, push or claim install-ready. No commit/tag/release/push performed.
