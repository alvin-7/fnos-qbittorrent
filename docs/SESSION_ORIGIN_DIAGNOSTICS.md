# Session-origin diagnostic boundary

## Finding

The fnOS app contract documents that `gatewayPrefix` and `gatewaySocket` select the Unix-socket route and that fnOS authenticates before forwarding user headers. The repository's socket implementation additionally enforces `0660` on the socket, `0770` on its parent, package UID ownership, and strips client-supplied `X-Trim-*`/forwarding headers before qB. This is a trusted transport/authentication boundary, but it does **not** expose a signed or otherwise authoritative canonical public HTTP authority to the application. The socket peer therefore cannot prove whether the browser used the desktop, LAN, FN Connect, or another gateway authority.

Consequently, the safe behavior is diagnosis only: retain exact origin binding and do not auto-rebind or add an origin allowlist based on the socket path.

## Implemented behavior

On `session_origin_mismatch`, the gateway still returns HTTP 403 and `X-Fnos-Gateway-Reason: session_origin_mismatch`, increments an in-memory security-event counter, and returns only:

- keyed, per-process 12-hex-character HMAC-SHA256 fingerprints for the saved and requested origin;
- scheme/port class (`http-default`, `https-default`, `http-nondefault`, `https-nondefault`);
- `bootstrap_origin_changed: true`.

No hostname, URL, cookie, token, query, or credential is returned. The fingerprint key is not persisted or exposed, so it is an equality diagnostic rather than an authority identifier. Existing UID, CSRF, Fetch Metadata, Origin/Referer validation, Unix-socket boundary, and exact origin comparison remain mandatory.

The frontend consumes the JSON diagnostic for the fixed error message; it never retries a business mutation. The existing safe GET recovery remains unchanged.

## Not implemented deliberately

No “canonical origin” repair was added. Accepting an arbitrary `Origin`, trusting the Host header, or treating any public/LAN origin as equivalent would weaken the current binding and cannot be justified by the available fnOS socket data. A future mobile strategy requires fnOS to provide an authenticated, application-scoped canonical-authority assertion (bound to the same session/UID and protected from client injection) before it can be considered.
