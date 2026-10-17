package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestNativeExpiredSessionAndWrongPassword(t *testing.T) {
	var logins, mutations int
	valid := "fresh"
	b := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path == "/api/v2/auth/login" {
			logins++
			r.ParseForm()
			if r.Form.Get("password") != "secret" {
				io.WriteString(w, "Fails.")
				return
			}
			http.SetCookie(w, &http.Cookie{Name: "QBT_SID_18080", Value: valid})
			w.WriteHeader(204)
			return
		}
		if r.Header.Get("Cookie") != "QBT_SID_18080="+valid {
			w.WriteHeader(403)
			return
		}
		if r.Method == "POST" {
			mutations++
		}
		io.WriteString(w, "v5.2.4")
	}))
	defer b.Close()
	file := filepath.Join(t.TempDir(), "password")
	os.WriteFile(file, []byte("secret"), 0600)
	t.Setenv("BACKEND_PASSWORD_FILE", file)
	t.Setenv("BACKEND_COOKIE", "QBT_SID_18080=expired")
	p, _ := newProxy(b.URL)
	request := func(method, path, body string) int {
		r := httptest.NewRequest(method, prefix+path, strings.NewReader(body))
		r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		p.ServeHTTP(w, r)
		return w.Code
	}
	if c := request("POST", "/api/v2/torrents/delete", "hashes=test"); c != 200 || logins != 1 || mutations != 1 {
		t.Fatalf("expired: status=%d login=%d mutations=%d", c, logins, mutations)
	}
	valid = "after-restart"
	if request("GET", "/api/v2/app/version", "") != 200 || logins != 2 {
		t.Fatal("restart did not recover")
	}
	valid = "again"
	os.WriteFile(file, []byte("wrong"), 0600)
	for i := 0; i < 3; i++ {
		if request("POST", "/api/v2/torrents/delete", "hashes=test") != 503 {
			t.Fatal("wrong password not closed")
		}
	}
	if logins != 3 || mutations != 1 {
		t.Fatalf("failure loop or duplicate mutation: login=%d mutations=%d", logins, mutations)
	}
}
func TestNativeCredentialPreferenceBlocked(t *testing.T) {
	t.Setenv("BACKEND_PASSWORD_FILE", "/nonexistent")
	p, _ := newProxy("http://127.0.0.1:1")
	for _, body := range []string{`json={"web_ui_password":"bad"}`, `json={"web_ui_username":"bad"}`, `json={"web_ui_localhost_auth":false}`, `json=oops`, `json={"dl_limit":1}&json={"web_ui_password":"bad"}`} {
		r := httptest.NewRequest("POST", prefix+"/api/v2/app/setPreferences", strings.NewReader(body))
		r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		w := httptest.NewRecorder()
		p.ServeHTTP(w, r)
		if w.Code != 403 && w.Code != 400 {
			t.Fatalf("not rejected: %d", w.Code)
		}
	}
}
