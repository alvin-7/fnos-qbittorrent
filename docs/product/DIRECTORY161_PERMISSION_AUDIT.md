# 1.5.11 permission audit

## Field evidence narrowed, not closed

The 1.5.10 picker label `读取权限拒绝` reads only the counter `package_read_denied`. With scanned=1, returned=0 and this counter=1, the first child inspection's `openat(O_RDONLY|O_DIRECTORY|O_NOFOLLOW)` failed with EACCES/EPERM. That child never reached `checked()` or `trim.file.checkUserACL`. An ACL API denial instead increments `aclDenied`; mount/link rejection used `mount_rejected`. The field report therefore points to the worker/package OS access layer, NOT a demonstrated checkUserACL denial. The NAS has not been accessed.

The visible fnOS read/write grant can refer to the application grant record or the logged-in user. Neither proves qb-native's OS UID/groups/ACL, inheritance on this child, or its mount namespace. No chmod 777, global traversal, authorization bypass or repeated blind grants are justified.

## Real defect and scope

A separately reproduced defect affected relative paths with execute-only intermediate directories: directoryWork opened every relative component O_RDONLY. A readable leaf behind an execute-only intermediate returned package_read_denied despite valid traversal. New regression failed before the fix and passed afterward. Intermediates now use O_PATH|O_DIRECTORY|O_NOFOLLOW, final directories still require O_RDONLY. This does NOT make an unreadable immediate child enumerable and is NOT claimed to explain the NAS's one-child failure.

Symlinks remain rejected. ENOTDIR alone no longer means mount rejection: a no-follow O_PATH/Fstat probe classifies links separately, closes the probe, and never authorizes a failed open. Real tmpfs/bind descendants are permitted subject to per-child platform ACL; only confirmed root dev/inode/mount identity is pinned.

## Safe fixed counters

- ACL_API_DENIED: successful checkUserACL response with readable=false (user_acl).
- PACKAGE_OPEN_EACCES: package filesystem EACCES/EPERM, not platform API refusal.
- MOUNT_REJECTED: confirmed root identity changed.
- SYMLINK_REJECTED: no-follow link rejection.
- child_open_rejected vs childRejected separates scan/open from subsequent child checks.

Diagnostics include only fixed stage and integer aggregates; no rejected names, paths, raw messages, UIDs or tokens. Existing successful canonical-path fields remain the authorized picker contract, not diagnostic disclosure.

## Local evidence

- RED: TestDirectoryRelativeTraverseOnlyIntermediate returned 404/package_read_denied; new origin-counter assertions failed on the original source.
- GREEN: full gateway/native Go suites; TypeScript/Vite build.
- Existing real private user/mount namespace tmpfs+bind regression passed.
- Real POSIX named-user ACL on differently-owned child: UID/GID 1000:1000 opened successfully; UID/GID 2001:2001 returned package_read_denied. Read-only container mount correctly kept Writable=false. This is a Linux ACL proof, not fnOS Windows ACL proof.
- Execute-only final directory remains rejected; ACL-denied readable child and symlink remain rejected; root replacement returns MOUNT_REJECTED.
- Exact 1.5.11 FPK gateway exercised against the fixed official Unix socket with simulated provider: two roots, real tmpfs child, child ACL/schema denial, token/scope refusal and symlink rejection PASS. It does not prove actual NAS API/permissions.
- Build verified 249 packaged files against staging; prior release hashes unchanged. Locked runtime reused, not a clean native runtime rebuild.

## Minimal on-site read-only check

Ask the NAS administrator to run the following locally, enter ONLY the exact rejected child's existing path at the silent read, and return just the booleans. It makes no filesystem writes and prints no path or account IDs:

```sh
sudo -u qb-native -- sh -c '
IFS= read -r p
r=false; x=false; d=false
[ -r "$p" ] && r=true
[ -x "$p" ] && x=true
[ -d "$p" ] && d=true
printf "read=%s execute=%s directory=%s\n" "$r" "$x" "$d"
'
```

The path is stdin, not a command-line argument. Do not send passwords in chat. If sudo/runuser is unavailable, an administrator must use the NAS-supported equivalent; do not change permissions as a probe. This creates a fresh qb-native process and may not reproduce a running package's supplementary groups or mount namespace. If all booleans are true yet the installed worker reports PACKAGE_OPEN_EACCES, compare the actual service namespace/group initialization locally; do not conclude the grant API is wrong.

## Artifact and remaining acceptance

FPK: release/fnos-qbittorrent-native-1.5.11-x86_64.fpk
SHA256: 62ef1ab72b2507fe8ace3b40025c4e39cdfb6689756d1221fc43e74d8379916f
Source: release/native-1.5.11-source-bundle.tar.gz
SHA256: f0aaf82bc3829706e730782b10ff10d925694fa5c9d7b17a61caa69b53c1e7d9

verified: local code regressions, actual Linux identity/ACL checks, exact packaged gateway production transport tests, packaged file equality.
implemented_unverified: final packaged diagnostic labels in a real browser/iframe.
blocked: NAS qb-native identity/ACL/ns and real fnOS API acceptance; physical mobile acceptance.

The packaged verification harness and this audit are additive post-freeze verification files; do not claim they exist in the frozen source bundle. Do not present this candidate as the verified NAS incident fix.
