# 1.5.5 focused final-artifact acceptance

## Outcome

1.5.4 is superseded, not overwritten. Its final packaged UI reproducibly lost task scroll (600 → 0) after Analysis → Return at 1440/390/360. `src/main.tsx` now records task/analysis scroll separately and restores in layout effect; choosing a new site intentionally starts the filtered task view at top. No historical npm assertions were changed.

Final immutable candidate: `release/fnos-qbittorrent-native-1.5.5-x86_64.fpk`, matching `native-1.5.5-source-bundle.tar.gz`. Locked 1.4.8 native runtime reuse, not a clean runtime rebuild.

## Final artifact gates

| Requirement | Status | Exact evidence / scope |
|---|---|---|
| Production gateway provider success | PASS | `workspace155-production.json`; gateway extracted directly from final FPK, not a Go test binary; private user/mount/network namespace, isolated `/run`, actual fixed `/var/run/trim_open_gateway_apiscope.socket`; localhost-only namespace, no external connectivity |
| Four authorized roots | PASS | Real qB preferences save/readback and isolated stopped fixture task savepath/readback at each root; same-label roots plus Chinese/space descendant |
| Storage identity dedup | PASS | Four real roots on one actual filesystem → one volume, four roots; total compared to actual statvfs, used=total-free |
| Private completed site aggregation | PASS | Actual qB 5.2.4 private properties, one completed stopped private task, eligible hash exactly once, no running hash; trackerless fixture produces unknown domain; complex multi-domain dedup remains existing Go test evidence rather than a new real multi-domain fixture claim |
| Permission failures | PASS | Simulated official fnOS code 200003 at both shared_grants/user_acl → AUTH_SCOPE_DENIED; zero new tasks on denied add; raw platform message absent; missing token fails closed |
| Packaged iframe 1440/390/360 | PASS | Existing focused browser checks rerun using FPK-extracted webui and production gateway: analysis/no frontend raw tracker reads, directory nested locks, batch stop readback, detail, settings/rate/ratio and no horizontal overflow |
| Category/tag/site same workspace | PASS | `workspace155-contracts.json`; real backend category/tag assigned to private fixture, resource labels, site return and one summary, no separate task page |
| Clear filters | PASS | Clear removes category/tag/site summary and resets status to all |
| Task scroll return | PASS | 600 → 600 all three widths; desktop harness activates navigation without Playwright auto-scroll changing the saved task position |
| Dock/FAB/selection | PASS | Dock and FAB present in mobile normal view, absent in selection; existing overlay and Analysis suppression checks rerun |
| Connector sessions / restart | PASS | Final production gateway: wrong password denial, valid login/protected version read, password rotation revokes old session, enabled restart persists config but invalidates old session, login after restart succeeds; disable then restart remains disabled and TCP connection refused |
| Artifact byte binding / resource scopes | PASS | `workspace155-artifact.json`: 249 app files match staging; duplicate resource members inspected; FPK app.tgz manifest MD5 checked; all prior release file SHA256 unchanged during build |
| Historical npm suite | NOT A CURRENT GATE | Legacy fixtures/layout assertions are not substituted for current requirements; no blind updates, no claim of complete historical suite PASS |
| NAS, qb-native UID/ACL and physical phone | BLOCKED / out of scope | Namespace UID 0 maps to host user 1000; this is neither root on NAS nor proof of package-account/Windows ACL. Unix API is a local simulation of official transport, not real platform authorization |
| Full historical MoviePilot/Docker suite | NOT REPEATED | Existing 1.5.4 sibling Docker evidence remains separate; this run proves production session/restart locally, not every historical timeout/source-mapping scenario |

## Safe reproduction

```sh
unshare -Urnm sh -c 'mount -t tmpfs tmpfs /run && ip link set lo up && CONTRACT_EVIDENCE=evidence/workspace155-contracts.json python3 tools/verify_workspace155_production.py'
```

Only isolated synthetic tasks and generated credentials were used; token and session values were not printed. No NAS, real tasks, real credentials, Git commit/push/tag/release operations. Do not claim production readiness beyond the named local gates.

The original source bundle was frozen at build; later harness-only corrections are delivered in an additive hashed verification overlay, not injected into the immutable FPK/source tarball.
