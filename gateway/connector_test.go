package main

import (
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"testing"
)

func TestConnectorDisabledAndNetworkValidation(t *testing.T) {
	c := newConnector(t.TempDir(), nil)
	if c.status().Listening {
		t.Fatal("default listener open")
	}
	for _, ip := range []string{"host.docker.internal", "::", "203.0.113.123"} {
		err := c.configure(connectorInput{Enabled: true, BindIP: ip, Port: 18081, Username: "automation", Password: "isolated-test-password-42", AllowedCIDRs: []string{"127.0.0.1/32"}, TrustedHTTP: true})
		if err == nil {
			t.Fatal("accepted invalid/non-local binding", ip)
		}
	}
}
func TestConnectorSessionPolicyAndRevoke(t *testing.T) {
	c := newConnector(t.TempDir(), http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("v5.2.4")) }))
	cfg := connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18981, Username: "automation", Password: "isolated-test-password-42", AllowedCIDRs: []string{"127.0.0.1/32"}, TrustedHTTP: true}
	if err := c.configure(cfg); err != nil {
		t.Fatal(err)
	}
	defer c.close()
	login := func(password string) *httptest.ResponseRecorder {
		r := httptest.NewRequest("POST", "http://host.docker.internal:18981/api/v2/auth/login", strings.NewReader(url.Values{"username": {"automation"}, "password": {password}}.Encode()))
		r.RemoteAddr = "127.0.0.1:12345"
		r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		c.ServeHTTP(w, r)
		return w
	}
	if login("wrong").Code != 403 {
		t.Fatal("wrong credential accepted")
	}
	w := login(cfg.Password)
	if w.Code != 200 || len(w.Result().Cookies()) != 1 {
		t.Fatal("standard login failed", w.Code)
	}
	cookie := w.Result().Cookies()[0]
	get := func(path, origin, peer string) *httptest.ResponseRecorder {
		r := httptest.NewRequest("GET", "http://host.docker.internal:18981/api/v2/"+path, nil)
		r.RemoteAddr = peer
		r.AddCookie(cookie)
		if origin != "" {
			r.Header.Set("Origin", origin)
		}
		w := httptest.NewRecorder()
		c.ServeHTTP(w, r)
		return w
	}
	if get("app/version", "", "127.0.0.1:1").Code != 200 {
		t.Fatal("session not usable")
	}
	for _, p := range []string{"connector/configure", "../socket", "socket/file/path", "diagnostics/add"} {
		if get(p, "", "127.0.0.1:1").Code == 200 {
			t.Fatal("allowlist escaped", p)
		}
	}
	if get("app/version", "http://evil.invalid", "127.0.0.1:1").Code != 403 {
		t.Fatal("origin accepted")
	}
	if get("app/version", "", "127.0.0.2:1").Code != 403 {
		t.Fatal("source accepted")
	}
	cfg.Password = "changed-isolated-password-84"
	if err := c.configure(cfg); err != nil {
		t.Fatal(err)
	}
	if get("app/version", "", "127.0.0.1:1").Code != 403 {
		t.Fatal("old session survived rotation")
	}
	for _, p := range []string{c.dir, c.file()} {
		s, e := os.Stat(p)
		if e != nil {
			t.Fatal(e)
		}
		want := os.FileMode(0600)
		if p == c.dir {
			want = 0700
		}
		if s.Mode().Perm() != want {
			t.Fatal("secret permissions", s.Mode())
		}
	}
	cfg.Enabled = false
	cfg.Password = ""
	if err := c.configure(cfg); err != nil {
		t.Fatal(err)
	}
	if c.status().Listening {
		t.Fatal("disable did not close listener")
	}
}

func TestConnectorAcceptsLongUTF8PasswordAndRejectsControls(t *testing.T) {
	c := newConnector(t.TempDir(), http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.Write([]byte("v5.2.4")) }))
	defer c.close()
	password := strings.Repeat("长", 256) // 768 UTF-8 bytes, above the old 16-byte cap.
	cfg := connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18983, Username: "automation", Password: password, AllowedCIDRs: []string{"127.0.0.1/32"}, TrustedHTTP: true}
	if err := c.configure(cfg); err != nil {
		t.Fatal("long UTF-8 password rejected:", err)
	}
	login := httptest.NewRequest("POST", "http://host.docker.internal:18983/api/v2/auth/login", strings.NewReader(url.Values{"username": {"automation"}, "password": {password}}.Encode()))
	login.RemoteAddr = "127.0.0.1:12345"
	login.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	c.ServeHTTP(w, login)
	if w.Code != 200 {
		t.Fatalf("long UTF-8 login failed: %d", w.Code)
	}
	for _, bad := range []string{"valid\npassword", "valid\rpassword", "valid\x00password"} {
		cfg.Password = bad
		if err := c.configure(cfg); err == nil {
			t.Fatalf("control password accepted: %q", bad)
		}
	}
}
