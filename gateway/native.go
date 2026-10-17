package main

// Native backend credentials never enter client cookies or diagnostics.
// Preflight authentication BEFORE dispatching any request; never replay mutations.
import (
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

type nativeTransport struct {
	sync.Mutex
	base                          http.RoundTripper
	backend, passwordFile, cookie string
	failedUntil                   time.Time
	diagnostics                   map[string]diagnosticCursor
}

func nativeResponse(code int) *http.Response {
	return &http.Response{StatusCode: code, Header: make(http.Header), Body: io.NopCloser(strings.NewReader("native backend request unavailable"))}
}
func nativePolicyResponse() *http.Response {
	r := nativeResponse(403)
	r.Header.Set("X-Fnos-Gateway-Reason", "native_policy_forbidden")
	return r
}
func (t *nativeTransport) probe() bool {
	r, _ := http.NewRequest("GET", t.backend+"/api/v2/app/version", nil)
	r.Header.Set("Cookie", t.cookie)
	r.Host = "127.0.0.1:18080"
	res, e := t.base.RoundTrip(r)
	if e != nil {
		return false
	}
	defer res.Body.Close()
	b, _ := io.ReadAll(io.LimitReader(res.Body, 256))
	return res.StatusCode == 200 && string(b) == "v5.2.4"
}
func (t *nativeTransport) authenticate() bool {
	if t.probe() {
		return true
	}
	if time.Now().Before(t.failedUntil) {
		return false
	}
	// Exactly one login attempt, then a cooldown; no login loops or transport replay.
	t.failedUntil = time.Now().Add(time.Minute)
	b, e := os.ReadFile(t.passwordFile)
	if e != nil {
		return false
	}
	r, _ := http.NewRequest("POST", t.backend+"/api/v2/auth/login", strings.NewReader(url.Values{"username": {"admin"}, "password": {strings.TrimSpace(string(b))}}.Encode()))
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	r.Host = "127.0.0.1:18080"
	res, e := t.base.RoundTrip(r)
	if e != nil {
		return false
	}
	io.Copy(io.Discard, res.Body)
	res.Body.Close()
	if res.StatusCode != 200 && res.StatusCode != 204 {
		return false
	}
	for _, c := range res.Cookies() {
		if strings.Contains(c.Name, "SID") {
			t.cookie = c.Name + "=" + c.Value
			if t.probe() {
				t.failedUntil = time.Time{}
				return true
			}
		}
	}
	return false
}
func (t *nativeTransport) RoundTrip(r *http.Request) (*http.Response, error) {
	t.Lock()
	defer t.Unlock()
	if strings.HasPrefix(r.URL.Path, "/api/v2/auth/") {
		return nativePolicyResponse(), nil
	}
	if r.URL.Path == "/api/v2/app/setPreferences" {
		// Reject ambiguous encodings, duplicate JSON fields and all backend WebUI
		// configuration. Non-WebUI settings retain normal qB behavior.
		if r.Method != "POST" || r.ParseForm() != nil || len(r.Form["json"]) != 1 {
			return nativeResponse(400), nil
		}
		var prefs map[string]json.RawMessage
		if json.Unmarshal([]byte(r.Form.Get("json")), &prefs) != nil || prefs == nil {
			return nativeResponse(400), nil
		}
		for k := range prefs {
			if strings.HasPrefix(strings.ToLower(k), "web_ui_") {
				return nativePolicyResponse(), nil
			}
		}
		body := r.PostForm.Encode()
		r.Body = io.NopCloser(strings.NewReader(body))
		r.ContentLength = int64(len(body))
		r.GetBody = nil
	}
	if !t.authenticate() {
		return nativeResponse(503), nil
	}
	if r.URL.Path == "/api/v2/diagnostics/add" {
		return t.addDiagnostics(r), nil
	}
	r.Header.Set("Cookie", t.cookie)
	res, e := t.base.RoundTrip(r)
	// A session can expire between probe and mutation. Return its failure without
	// replay: the caller must explicitly decide whether to resubmit.
	if res != nil {
		res.Header.Del("Set-Cookie")
	}
	return res, e
}
