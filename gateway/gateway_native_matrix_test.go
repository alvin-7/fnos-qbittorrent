package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestNativeGatewaySecurityMatrix(t *testing.T) {
	for _, method := range []string{"GET", "POST"} {
		for _, tc := range []struct {
			name, uid, admin, origin, referer, site, marker, path string
			trusted                                               bool
			want                                                  int
		}{
			{"webview-no-cookie", "1000", "true", "https://phone.invalid", "https://phone.invalid/app/", "", "gateway-request-v1", "api/v2/torrents/info", true, 204},
			{"rewritten-authority", "1000", "true", "https://new-authority.invalid:8443", "", "same-origin", "gateway-request-v1", "api/v2/torrents/info", true, 204},
			{"missing-uid", "", "true", "https://phone.invalid", "", "", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"not-admin", "1000", "false", "https://phone.invalid", "", "", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"public-spoof", "1000", "true", "https://phone.invalid", "", "same-origin", "gateway-request-v1", "api/v2/torrents/info", false, 403},
			{"cross-site", "1000", "true", "https://evil.invalid", "", "cross-site", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"same-site", "1000", "true", "https://evil.invalid", "", "same-site", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"null-origin", "1000", "true", "null", "", "", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"missing-source", "1000", "true", "", "", "", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"origin-referrer-disagree", "1000", "true", "https://a.invalid", "https://b.invalid/", "", "gateway-request-v1", "api/v2/torrents/info", true, 403},
			{"simple-form", "1000", "true", "https://evil.invalid", "", "", "", "api/v2/torrents/info", true, 403},
			{"invalid-identity", "attacker", "true", "https://phone.invalid", "", "", "gateway-request-v1", "api/v2/torrents/info", true, 403},
		} {
			t.Run(method+tc.name, func(t *testing.T) {
				calls := 0
				h := nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { calls++; w.WriteHeader(204) }))
				r := httptest.NewRequest(method, prefix+"/"+tc.path, nil)
				r = r.WithContext(context.WithValue(r.Context(), gatewayUnixContextKey{}, tc.trusted))
				for k, v := range map[string]string{"X-Trim-Userid": tc.uid, "X-Trim-Isadmin": tc.admin, "Origin": tc.origin, "Referer": tc.referer, "Sec-Fetch-Site": tc.site, csrfHeader: tc.marker} {
					if v != "" {
						r.Header.Set(k, v)
					}
				}
				w := httptest.NewRecorder()
				h.ServeHTTP(w, r)
				if w.Code != tc.want {
					t.Fatalf("got %d want %d", w.Code, tc.want)
				}
				if tc.want == 403 && calls != 0 {
					t.Fatal("rejected forwarded")
				}
			})
		}
	}
	for _, path := range []string{"/", "/assets/a.js", "/api/v2/torrents/delete"} {
		r := httptest.NewRequest("GET", prefix+path, nil)
		w := httptest.NewRecorder()
		nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Fatal("unauth forwarded") })).ServeHTTP(w, r)
		if w.Code != 403 {
			t.Fatal(path, w.Code)
		}
	}
	r := httptest.NewRequest("GET", prefix+"/api/v2/torrents/delete", nil).WithContext(context.WithValue(context.Background(), gatewayUnixContextKey{}, true))
	r.Header.Set("X-Trim-Userid", "1000")
	r.Header.Set("X-Trim-Isadmin", "true")
	r.Header.Set("Origin", "https://phone.invalid")
	r.Header.Set(csrfHeader, "gateway-request-v1")
	w := httptest.NewRecorder()
	nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Fatal("GET mutation forwarded") })).ServeHTTP(w, r)
	if w.Code != 403 {
		t.Fatal(w.Code)
	}
}
