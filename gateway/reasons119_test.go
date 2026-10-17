package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"
)

func TestSafeReasonsAndUA(t *testing.T) {
	s := newSessionStore()
	h := gatewayHandlerStore(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(204) }), s)
	request := func(path, origin, referer, site, uid, cookie, token, ua string) *httptest.ResponseRecorder {
		r := httptest.NewRequest("POST", prefix+path, nil)
		for k, v := range map[string]string{"Origin": origin, "Referer": referer, "Sec-Fetch-Site": site, "X-Trim-Userid": uid, "X-Trim-Isadmin": "true", "X-Fnos-Bootstrap": "1", "Cookie": cookie, csrfHeader: token, "User-Agent": ua} {
			if v != "" {
				r.Header.Set(k, v)
			}
		}
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		return w
	}
	o := "https://test.example"
	b := request("/gateway/session", o, "", "", "1000", "", "", "Chrome Mobile")
	if b.Code != 200 {
		t.Fatal(b.Code)
	}
	var d map[string]any
	json.Unmarshal(b.Body.Bytes(), &d)
	token := d["token"].(string)
	c := b.Result().Cookies()[0]
	cookie := c.Name + "=" + c.Value
	if c.Path != prefix+"/" {
		t.Fatal(c.Path)
	}
	for _, tc := range []struct{ origin, referer, site, uid, cookie, token, reason string }{{o, "", "", "", cookie, token, "missing_trim_identity"}, {"", "", "", "1000", cookie, token, "origin_or_referer_missing"}, {o, "https://other.example/", "", "1000", cookie, token, "origin_referer_mismatch"}, {o, "", "same-site", "1000", cookie, token, "fetch_site_not_same_origin"}, {o, "", "", "1000", "", token, "session_cookie_missing"}, {"https://other.example", "", "", "1000", cookie, token, "session_origin_mismatch"}, {o, "", "", "2000", cookie, token, "session_uid_mismatch"}, {o, "", "", "1000", cookie, "", "csrf_missing_or_invalid"}} {
		w := request("/api/v2/torrents/stop", tc.origin, tc.referer, tc.site, tc.uid, tc.cookie, tc.token, "any UA")
		if w.Code != 403 || w.Header().Get("X-Fnos-Gateway-Reason") != tc.reason {
			t.Fatalf("%s got %d %s", tc.reason, w.Code, w.Header().Get("X-Fnos-Gateway-Reason"))
		}
	}
	for _, ua := range []string{"Chrome Desktop", "Chrome Mobile", "WebView", ""} {
		for _, site := range []string{"", "same-origin"} {
			w := request("/api/v2/torrents/stop", o, "", site, "1000", cookie, token, ua)
			if w.Code != 204 {
				t.Fatal(ua, site, w.Code)
			}
		}
	}
	s.now = func() time.Time { return time.Now().Add(sessionTTL + time.Second) }
	w := request("/api/v2/torrents/stop", o, "", "", "1000", cookie, token, "")
	if w.Header().Get("X-Fnos-Gateway-Reason") != "session_expired" {
		t.Fatal("expiry reason")
	}
}
