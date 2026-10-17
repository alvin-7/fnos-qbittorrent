package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestSessionSecurity(t *testing.T) {
	store := newSessionStore()
	calls := 0
	h := gatewayHandlerStore(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { calls++; w.WriteHeader(204) }), store)
	req := func(path, method, origin, cookie, token string) *httptest.ResponseRecorder {
		r := httptest.NewRequest(method, prefix+path, nil)
		r.Host = "localhost"
		r.Header.Set("Referer", origin+prefix+"/")
		r.Header.Set("X-Trim-Userid", "1000")
		r.Header.Set("X-Trim-Isadmin", "true")
		r.Header.Set("X-Fnos-Bootstrap", "1")
		if cookie != "" {
			r.Header.Set("Cookie", cookie)
		}
		if token != "" {
			r.Header.Set(csrfHeader, token)
		}
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w
	}
	origin := "https://any.external.example:444"
	b := req("/gateway/session", "POST", origin, "", "")
	if b.Code != 200 {
		t.Fatal(b.Code)
	}
	var data map[string]any
	_ = json.Unmarshal(b.Body.Bytes(), &data)
	token := data["token"].(string)
	c := b.Result().Cookies()[0]
	cookie := c.Name + "=" + c.Value
	if !c.HttpOnly || !c.Secure || c.Path != prefix+"/" || c.SameSite != http.SameSiteNoneMode || b.Header().Get("Cache-Control") != "no-store" {
		t.Fatal("cookie/cache policy")
	}
	for _, tc := range []struct {
		origin, cookie, token string
		code                  int
	}{{origin, cookie, token, 204}, {origin, cookie, "", 403}, {origin, "", token, 403}, {"https://evil.example", cookie, token, 403}, {"http://any.external.example:444", cookie, token, 403}, {origin, cookie, "wrong", 403}} {
		w := req("/api/v2/app/setPreferences", "POST", tc.origin, tc.cookie, tc.token)
		if w.Code != tc.code {
			t.Fatal(tc, w.Code)
		}
	}
	for _, site := range []string{"cross-site", "same-site"} {
		r := httptest.NewRequest("POST", prefix+"/gateway/session", nil)
		r.Header.Set("X-Trim-Userid", "1000")
		r.Header.Set("X-Trim-Isadmin", "true")
		r.Header.Set("X-Fnos-Bootstrap", "1")
		r.Header.Set("Origin", origin)
		r.Header.Set("Sec-Fetch-Site", site)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != 403 {
			t.Fatal(site, w.Code)
		}
	}
	if req("/gateway/session?token=secret", "POST", origin, cookie, token).Code != 403 {
		t.Fatal("query")
	}
	if req("/gateway/logout", "POST", origin, cookie, token).Code != 204 || req("/api/v2/app/preferences", "GET", origin, cookie, token).Code != 403 {
		t.Fatal("logout")
	}
	b = req("/gateway/session", "POST", origin, "", "")
	_ = json.Unmarshal(b.Body.Bytes(), &data)
	token = data["token"].(string)
	c = b.Result().Cookies()[0]
	cookie = c.Name + "=" + c.Value
	store.now = func() time.Time { return time.Now().Add(sessionTTL + time.Second) }
	if req("/api/v2/app/preferences", "GET", origin, cookie, token).Code != 403 {
		t.Fatal("expiry")
	}
	if len(store.sessions) != 0 {
		t.Fatal("expired entries retained")
	}
	store.now = time.Now
	for i := 0; i < maxSessions; i++ {
		store.sessions[string(rune(i))] = gatewaySession{expires: time.Now().Add(time.Hour)}
	}
	if req("/gateway/session", "POST", origin, "", "").Code != 503 {
		t.Fatal("capacity")
	}
	if calls != 1 {
		t.Fatal("rejected request reached backend", calls)
	}
}

func TestHTTPSBootstrapCookieSupportsEmbeddedWebView(t *testing.T) {
	store := newSessionStore()
	h := gatewayHandlerStore(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(204) }), store)
	r := httptest.NewRequest("POST", prefix+"/gateway/session", nil)
	r.Header.Set("Origin", "https://nas.example")
	r.Header.Set("X-Trim-Userid", "1000")
	r.Header.Set("X-Trim-Isadmin", "true")
	r.Header.Set("X-Fnos-Bootstrap", "1")
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	if w.Code != http.StatusOK {
		t.Fatalf("status=%d", w.Code)
	}
	c := w.Result().Cookies()[0]
	if c.SameSite != http.SameSiteNoneMode || !c.Secure || !c.HttpOnly || c.Path != prefix+"/" {
		t.Fatalf("cookie policy: %+v", c)
	}
}
