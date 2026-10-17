package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
)

func TestNativeNeverReplaysMutationAfterSuccessfulProbe(t *testing.T) {
	var calls int32
	b := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v2/app/version" {
			w.Write([]byte("v5.2.4"))
			return
		}
		atomic.AddInt32(&calls, 1)
		w.WriteHeader(403)
	}))
	defer b.Close()
	t.Setenv("BACKEND_PASSWORD_FILE", "unused")
	t.Setenv("BACKEND_COOKIE", "QBT_SID_18080=valid-at-probe")
	p, _ := newProxy(b.URL)
	r := httptest.NewRequest("POST", prefix+"/api/v2/torrents/delete", strings.NewReader("hashes=test"))
	w := httptest.NewRecorder()
	p.ServeHTTP(w, r)
	if w.Code != 403 || calls != 1 {
		t.Fatalf("mutation replayed: status=%d calls=%d", w.Code, calls)
	}
}
func TestDockerProxyRetainsDirectCredentialAPI(t *testing.T) {
	t.Setenv("BACKEND_PASSWORD_FILE", "")
	var called bool
	b := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { called = true; w.WriteHeader(200) }))
	defer b.Close()
	p, _ := newProxy(b.URL)
	r := httptest.NewRequest("POST", prefix+"/api/v2/app/setPreferences", strings.NewReader(`json={"web_ui_password":"fixture"}`))
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	p.ServeHTTP(w, r)
	if w.Code != 200 || !called {
		t.Fatal("Docker mode credential API blocked")
	}
}
