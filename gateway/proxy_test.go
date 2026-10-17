package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(r *http.Request) (*http.Response, error) { return f(r) }

func TestProxyKeepsBackendHostAndStripsGatewayPrefix(t *testing.T) {
	var got *http.Request
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusNoContent)
	}))
	defer backend.Close()
	parsed, _ := url.Parse(backend.URL)
	proxy, err := newProxy(backend.URL)
	proxy.Transport = roundTripFunc(func(r *http.Request) (*http.Response, error) {
		got = r.Clone(r.Context())
		return http.DefaultTransport.RoundTrip(r)
	})
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodGet, prefix+"/api/v2/app/version?x=1", nil)
	req.Host = "gateway.example"
	req.Header.Set("X-Trim-Userid", "attacker")
	req.Header.Set("X-Trim-Isadmin", "true")
	req.Header.Set("X-Trim-Username", "attacker")
	req.Header.Set("Origin", "https://gateway.example")
	req.Header.Set("Referer", "https://gateway.example/app/fnos-qbittorrent/")
	rr := httptest.NewRecorder()
	proxy.ServeHTTP(rr, req)
	if rr.Code != http.StatusNoContent {
		t.Fatalf("status=%d body=%s", rr.Code, rr.Body.String())
	}
	if got == nil {
		t.Fatal("backend received no request")
	}
	if got.URL.Host != parsed.Host {
		t.Fatalf("URL host=%q, want %q", got.URL.Host, parsed.Host)
	}
	if got.URL.Path != "/api/v2/app/version" {
		t.Fatalf("path=%q", got.URL.Path)
	}
	if got.Host != "127.0.0.1:18080" {
		t.Fatalf("Host=%q", got.Host)
	}
	for _, h := range []string{"X-Trim-Userid", "X-Trim-Isadmin", "X-Trim-Username"} {
		if got.Header.Get(h) != "" {
			t.Fatalf("forwarded %s", h)
		}
	}
	if got.Header.Get("Origin") != "http://127.0.0.1:18080" || got.Header.Get("Referer") != "http://127.0.0.1:18080/" {
		t.Fatal("validated origin/referer not mapped to backend")
	}
	_, _ = io.Copy(io.Discard, rr.Body)
}

func TestProxyRejectsOutsidePrefix(t *testing.T) {
	proxy, err := newProxy("http://127.0.0.1:1")
	if err != nil {
		t.Fatal(err)
	}
	req := httptest.NewRequest(http.MethodGet, "/outside", nil)
	rr := httptest.NewRecorder()
	h := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != prefix && len(r.URL.Path) >= len(prefix)+1 && r.URL.Path[:len(prefix)+1] == prefix+"/" {
			proxy.ServeHTTP(w, r)
			return
		}
		http.NotFound(w, r)
	})
	h.ServeHTTP(rr, req)
	if rr.Code != http.StatusNotFound {
		t.Fatalf("status=%d", rr.Code)
	}
}

func TestNoSlashRedirect(t *testing.T) {
	h := gatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Fatal("must redirect before backend") }))
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, httptest.NewRequest("GET", prefix, nil))
	if rr.Code != 308 || rr.Header().Get("Location") != prefix+"/" {
		t.Fatalf("%d %s", rr.Code, rr.Header().Get("Location"))
	}
}

func TestNavigationExternalReferer(t *testing.T) {
	h := gatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Referer") != "" {
			t.Fatal("untrusted navigation referer forwarded")
		}
		w.WriteHeader(204)
	}))
	req := httptest.NewRequest("GET", prefix+"/", nil)
	req.Host = "internal.fn"
	req.Header.Set("Referer", "https://external.example/")
	req.Header.Set("Sec-Fetch-Site", "cross-site")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	if rr.Code != 204 {
		t.Fatalf("navigation=%d", rr.Code)
	}
}

func TestGatewayRejectsCrossOriginBeforeBackend(t *testing.T) {
	called := false
	h := gatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true; w.WriteHeader(204) }))
	for _, origin := range []string{"https://evil.test", "null", "https://gateway.example.evil.test"} {
		req := httptest.NewRequest("POST", prefix+"/api/v2/app/setPreferences", nil)
		req.Host = "gateway.example"
		req.Header.Set("Origin", origin)
		req.Header.Set("X-Trim-Isadmin", "true")
		rr := httptest.NewRecorder()
		h.ServeHTTP(rr, req)
		if rr.Code != 403 || called {
			t.Fatal("cross-origin reached backend")
		}
	}
}
