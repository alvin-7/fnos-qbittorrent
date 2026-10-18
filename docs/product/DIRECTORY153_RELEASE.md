# 1.5.3 scope delivery and safe diagnostics

## Confirmed package defect, not a unique NAS root cause

Official API calling documentation declares `config/resource` `api-scope` as a JSON array of strings. `getSharedAccessibleFolders` requires `trim.file.sharedAccess`; `checkUserACL` requires `trim.file.userAcl`; `trim.file.path` is the documented path-display conversion scope and is retained from the reviewed template (no path conversion API is currently invoked). Scope declarations do not grant arbitrary filesystem access.

References: https://developer.fnnas.com/api/calling/ , https://developer.fnnas.com/api/authorization/shared-access/ , https://developer.fnnas.com/api/authorization/file-acl/ , https://developer.fnnas.com/docs/core-concepts/resource/ . Official minimum capability versions are fnOS 1.2.0401 / App 1.34.0.

Historical 1.4.9–1.5.2 builders extract 1.4.8, then replace only outer resource with two scopes. The historical 1.5.2 audit fails the new three-scope assertion. The new builder explicitly writes reviewed template bytes to BOTH config/resource and app/config/resource, then checks every duplicate outer/inner member, including the effective last member. It builds current native-control as well as gateway and UI; previous native-control reuse would omit the multi-root initialization fix. Historical installers are never overwritten.

## Upgrade contract

App ID, package account, gateway prefix and `data-share.shares=[{"name":"fnos-qbittorrent-native/downloads"}]` remain unchanged. No uninstall, data relocation, share recreation, saved-path reset, task migration or secondary-root write is requested. Lifecycle multi-root tests check colon-separated environment parsing and existing default preservation.

Scope changes require platform registration/approval to take effect; upgrading bytes alone is not proof that an existing token gains scopes. Let the platform finish upgrade/permission confirmation and restart the application via fnOS, so its newly injected process token is used. Do not copy, inspect or persist tokens. If fnOS presents renewed permission confirmation, an administrator must approve it. If AUTH_SCOPE_DENIED persists, platform scope registration/approval is still a field acceptance gap; do not delete/recreate the four directory grants or uninstall as a first step.

## Diagnostic contract

Only fixed reason/stage strings and integer counts are returned on errors. Stage names: shared_grants, user_acl, root_filter. Counts cover discovered/unique/private exclusion/ACL checked-denied-errors/filesystem checked/package read denied/mount unavailable-rejected/other/available. ACL API errors immediately fail closed and never become empty roots. Homogeneous ACL denials, package read denials, absent/offline roots, mount/link rejection, private-only grants have specific fixed reasons; mixed failures retain AUTH_ROOTS_INACCESSIBLE with counts. Missing paths may mean missing directory OR mount, not proof of an offline physical volume. First-observation offline mount detection remains a platform gap. No paths, user IDs, tokens, upstream bodies/messages or operating-system error strings appear in diagnostic payloads. Authorized successful navigation necessarily returns its authorized paths; this prohibition concerns failure diagnostics.

## Acceptance boundaries

Local Go/race, TypeScript/npm, final packaged UI, real isolated qB 5.2.4 and test-only fnOS contract socket are separate from NAS acceptance. Local filesystem UID is not qb-native/Windows ACL proof. Four-root fixture contains duplicate basenames, Unicode/spaces, personal-style cross-volume layout, not actual four mounted NAS shares. No NAS, customer task or customer credentials are accessed. Do not claim the scope omission was the sole field cause or that NAS is repaired.

After installing: open **设置 → 选择目录 → 刷新授权状态** once. Expect the existing four authorized roots; otherwise return only the fixed visible reason code (never paths/token/raw logs).
