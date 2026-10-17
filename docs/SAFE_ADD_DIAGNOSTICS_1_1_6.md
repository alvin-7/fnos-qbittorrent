# Native 1.1.6 safe acquisition diagnostics — local acceptance

## Endpoint
`GET /app/fnos-qbittorrent-native/api/v2/diagnostics/add` captures the pre-submit high-water log ID and server time; returns an opaque random cursor. `GET .../diagnostics/add?cursor=<opaque>` reads only newer IDs with timestamp >= baseline. No source URL is accepted in the request. Cursors expire after 10 minutes; maximum 128; response up to 20 events; backend log JSON capped at 4 MiB. Backend auth failure/unreadable or invalid log results are unknown, not success. POST returns 405; other/duplicate query fields return 400. Invalid/expired cursor returns fixed unknown status. No logging/configuration API is mutated.

The endpoint remains behind the existing fnOS Unix-ingress identity, application session, origin/fetch metadata and X-Fnos-CSRF checks, including GET. Native qB authentication is preflighted; no business POST is replayed. It fetches warning/critical log entries internally using backend credentials. Raw messages remain transient server-only data, never in output/log statements. Event fields are integer time and fixed category/code/message/association only. The schema deliberately does not expose log ID, original message, URL, host, path, query, userinfo or credentials. Cursor is random (not a source credential).

Recognized signatures: DNS, TLS, HTTP 401/403/404, invalid torrent/bencoding; others return `未知错误，未输出原始日志`. Every event is explicitly `该时段后台错误，关联未确认`: a time window is not a proof of causality. No events is unknown, not success. Delayed errors outside the observation window may not appear; this is not a network repair.

## Actual execution
- `GO111MODULE=off go test -race ./gateway`: PASS (includes existing native/session/origin protections, synthetic DNS/TLS/HTTP/invalid/unknown classifications, privacy canaries, stale/no-log window, read-only/query constraints).
- `DIAGNOSTIC_BROWSER=1 python tools/verify_diagnostics_real.py`: PASS using isolated native real qB 5.2.4 and controlled local HTTP server. Real 404 and HTML/not-torrent generated real warning logs and returned safe categories. Packaged gateway and packaged iframe UI displayed HTTP_404 and INVALID_TORRENT plus association-unconfirmed; signed-query fixture created a new task unchanged. Exactly 3 business add POSTs, no replay. Endpoint statuses absent token/wrong token/valid token/source query/POST: 403/403/200/400/405.
- Test qB uses private profile and port 18116. A test-only bridge maps the packaged gateway's fixed 18080 Host/Origin to this alternate port without disabling qB CSRF/Host checks. Early setup failures were test Host/Origin mismatch, corrected in the final external test overlay. No NAS was contacted.
- Immutable FPK built and extracted-file audit passed: 25,038 original non-UI/non-gateway files preserved byte-for-byte, including original license tree and runtime. Gateway is rebuilt; new source is included. Corresponding runtime sources remain `release/native-1.1.4-sources.tar.gz` with original hash.

## Artifacts and source
FPK: `release/fnos-qbittorrent-native-1.1.6-x86_64.fpk`
SHA256: `93ed3c426f7d63d38d1da4067b1722ef1116c1dadcea880604567ba6654c8760`
Audit: `evidence/native-package-audit-1.1.6.json`
Browser acceptance: `evidence/diagnostics116-browser.json`
Final external overlay: `release/native-1.1.6-diagnostics-source-overlay.tar.gz` plus SHA256 sidecar. Includes current test-harness corrections made after immutable packaging; production Go/TS matches packaged source. The earlier `ui-source-overlay` and embedded tests predate those test-only corrections; do not use their browser harness for acceptance.

No Git repository exists here; nothing committed, published or installed on NAS. NAS transport/root cause and platform upgrade acceptance remain unverified. Original source/license distribution limitations remain unchanged.
