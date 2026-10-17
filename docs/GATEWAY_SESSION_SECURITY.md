# Unix gateway session security

## Interface and trust

The only adapter listener is Unix `app.sock` (0660, parent 0770). fnOS must authenticate every forwarded request, strip/overwrite client X-Trim identity, and enforce app permissions. Protected endpoints require fnOS administrator + nonempty UID. These headers are identity context only behind the socket; they are not standalone credentials. Never expose a TCP-to-socket bridge in deployment. The browser tests use one only as isolated test transport.

`POST /app/fnos-qbittorrent/gateway/session`, `X-Fnos-Bootstrap: 1`: browser Origin or Referer establishes scheme+authority despite fnOS Host rewriting. No domain list or forwarded-header trust. No CORS/preflight support. A browser's SOP and non-simple custom header prevent attacker-origin bootstrap; Sec-Fetch-Site, when supplied, must equal same-origin (same-site is insufficient). Missing Origin/Referer is rejected. The returned random 256-bit token is memory-only in `src/api.ts`, never query/localStorage. The independently random HttpOnly host-only cookie is scoped `/app/fnos-qbittorrent/`, SameSite Strict, Secure for HTTPS browser origin. Browser HTTPS is inferred from the validated source, not socket TLS or forwarded headers.

All prefixed API requests, including GET, require cookie + `X-Fnos-CSRF`, exact bound browser scheme+authority, and same fnOS UID/admin identity. Origin and Referer, if both provided, must agree. Safe HTML/static navigation alone does not need the application session; traversal is rejected before this exception. Backend Host/Origin/Referer map to qB loopback authority only after protection checks. qB Host and CSRF remain enabled. Adapter credentials and forwarded identity headers are stripped before qB.

Session lifetime is fixed 30 minutes, max 1024 sessions with expired-entry cleanup. At capacity bootstrap fails 503 rather than evicting active sessions. Logout (`POST gateway/logout` or `api/v2/auth/logout`) deletes the session and cookie. Restart drops every application session. fnOS logout blocks subsequent forwarding; app logout alone does not log out fnOS, and an authenticated fnOS administrator can bootstrap again. A copied application token cannot outlive its cookie, bound UID/origin, fnOS authentication, or fixed expiry.

The frontend single-flights bootstrap, and retries once only on the adapter's explicit pre-dispatch session rejection. Backend failures/network errors do not replay writes. Direct-root access does not bootstrap or send gateway credentials; qB native authentication is unchanged. Main exports retain API compatibility; components may import directly from `./api`.

## Verified evidence

- `evidence/gateway-session-unit.txt`: `GO111MODULE=off go test -race -v ./gateway` passed; source binding, missing token/cookie, cross-site/same-site rejection, lifetime, logout, capacity, source mapping.
- `npx tsc -b`: passed.
- `python3 tools/verify_gateway_session.py`: real isolated qB v5.2.4 + compiled Unix adapter + Chrome iframe. Both localhost and arbitrary.example browser origin work with backend incoming Host rewritten to localhost. Eight concurrent reads, real preference write/readback, logout/rebootstrap passed. Missing cookie/header and wrong token returned403. Malicious external bootstrap/fetch blocked by CORS; HTML form made no preference change. Forged X-Trim alone returned403. Restart invalidation passed. Direct qB native login/write200, bad Host401, bad Origin401, no-auth403 verified. Receipts: gateway-session-security.json and gateway-session-browser.json.

## Limits and remaining acceptance

No NAS was accessed or changed. Real fnOS login/permission enforcement, header replacement, Unix ownership/ACL, desktop WebView iframe and HTTPS browser cookie roundtrip still need platform acceptance. HTTPS Secure attributes were exercised over socket requests, not a real TLS browser endpoint. The browser test bundles the exact API client, not the parent's final packaged UI/FPK; final package rebuild/full-UI regression belongs to parent. Local qB image tag identifies real runtime version; locally imported image has no RepoDigests metadata, so this suite alone does not re-prove OCI digest provenance.

Socket compromise, same-origin script/XSS, malicious fnOS administrator, or an exposed trusted backend network are out of this CSRF threat model. Host rewriting means bootstrap cannot compare the browser origin against incoming Host; its safety depends on non-simple browser request + no CORS + private authenticated ingress. Non-browser clients with socket access can forge browser headers and are inherently trusted at this boundary. Global session cap bounds memory but not deliberate availability exhaustion by authenticated administrators. HTTP mode cannot protect against network interception: use HTTPS for normal deployment. Same-origin applications share the browser origin trust; cookie Path is scoping, not an isolation boundary.

Build adapter as the complete package (`GO111MODULE=off CGO_ENABLED=0 go build -o <target> ./gateway`), never only proxy.go. Legacy origin-generation script remains unused for backwards source compatibility; compose/prepare/wizard no longer depend on it. Earlier tools/verify_gateway.py and verify_gateway_browser.mjs encode old headerless API assumptions and are superseded by verify_gateway_session.py for this architecture.
