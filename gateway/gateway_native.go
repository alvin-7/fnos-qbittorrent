package main

// Native fnOS authentication is per-request, not an application cookie session.
import (
	"context"
	"encoding/json"
	"net"
	"net/http"
	"strings"
)

type gatewayUnixContextKey struct{}

func gatewayConnectionContext(ctx context.Context, c net.Conn) context.Context {
	_, ok := c.(*net.UnixConn)
	return context.WithValue(ctx, gatewayUnixContextKey{}, ok)
}

// qB permits some mutations via GET. Never infer safety from HTTP method alone.
var nativeReadRoutes = map[string]bool{
	"app/version": true, "app/webapiVersion": true, "app/preferences": true,
	"transfer/info": true, "transfer/speedLimitsMode": true,
	"torrents/info": true, "torrents/properties": true, "torrents/trackers": true,
	"torrents/webseeds": true, "torrents/files": true, "torrents/pieceStates": true,
	"torrents/pieceHashes": true, "sync/torrentPeers": true, "diagnostics/add": true,
	"torrents/categories": true, "torrents/tags": true, "connector/status": true, "connector/discover": true,
}

func nativeGatewayHandler(proxy http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Cache-Control", "no-store")
		w.Header().Set("Referrer-Policy", "same-origin")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		reject := func(reason string) {
			w.Header().Set("X-Fnos-Gateway-Reason", reason)
			http.Error(w, "fnOS gateway access rejected", 403)
		}
		if r.Context().Value(gatewayUnixContextKey{}) != true {
			reject("untrusted_gateway_transport")
			return
		}
		// Exactly one UID/admin header: ambiguous or comma-joined input is not identity.
		uid := r.Header.Get("X-Trim-Userid")
		if len(r.Header.Values("X-Trim-Userid")) != 1 || len(r.Header.Values("X-Trim-Isadmin")) != 1 || uid == "" || r.Header.Get("X-Trim-Isadmin") != "true" {
			reject("missing_trim_identity")
			return
		}
		for _, c := range uid {
			if c < '0' || c > '9' {
				reject("missing_trim_identity")
				return
			}
		}
		if r.URL.Path != prefix && !strings.HasPrefix(r.URL.Path, prefix+"/") {
			http.NotFound(w, r)
			return
		}
		if strings.Contains(r.URL.Path, "\\") || strings.Contains(r.URL.Path, "//") {
			http.NotFound(w, r)
			return
		}
		for _, part := range strings.Split(r.URL.Path, "/") {
			if part == "." || part == ".." {
				http.NotFound(w, r)
				return
			}
		}
		safe := r.Method == "GET" || r.Method == "HEAD"
		navigation := safe && (r.URL.Path == prefix || r.URL.Path == prefix+"/" || strings.HasPrefix(r.URL.Path, prefix+"/assets/"))
		if navigation {
			// Unrelated navigation referrers are not an API CSRF exception.
			r.Header.Del("Origin")
			r.Header.Del("Referer")
			if r.URL.Path == prefix {
				http.Redirect(w, r, prefix+"/", 308)
				return
			}
			proxy.ServeHTTP(w, r)
			return
		}
		// Non-simple marker + NO CORS is the primary CSRF boundary when fnOS
		// rewrites Host. This is NOT a secret/auth token. Browser SOP forbids sending
		// this header cross-origin without a successful preflight, always rejected.
		if r.Method == "OPTIONS" {
			reject("csrf_missing_or_invalid")
			return
		}
		if _, reason := browserSourceReason(r); reason != "" {
			reject(reason)
			return
		}
		bootstrap := r.URL.Path == prefix+"/gateway/session"
		if bootstrap {
			if r.Method != "POST" || r.Header.Get("X-Fnos-Bootstrap") != "1" || len(r.Header.Values("X-Fnos-Bootstrap")) != 1 || r.URL.RawQuery != "" {
				reject("csrf_missing_or_invalid")
				return
			}
			w.Header().Set("Content-Type", "application/json")
			json.NewEncoder(w).Encode(map[string]any{"token": "gateway-request-v1", "expiresIn": 0, "mode": "fnos-gateway"})
			return
		}
		if len(r.Header.Values(csrfHeader)) != 1 || r.Header.Get(csrfHeader) != "gateway-request-v1" {
			reject("csrf_missing_or_invalid")
			return
		}
		if r.URL.Path == prefix+"/api/v2/auth/logout" || r.URL.Path == prefix+"/gateway/logout" {
			if r.Method != "POST" {
				reject("csrf_missing_or_invalid")
				return
			}
			w.WriteHeader(204)
			return
		}
		route := strings.TrimPrefix(r.URL.Path, prefix+"/api/v2/")
		if route == r.URL.Path {
			http.NotFound(w, r)
			return
		}
		if safe && !nativeReadRoutes[route] {
			reject("native_policy_forbidden")
			return
		}
		if !safe && r.Method != "POST" {
			reject("native_policy_forbidden")
			return
		}
		r.Header.Del("Cookie") // never use browser session or backend SID at native ingress
		proxy.ServeHTTP(w, r)
	})
}
