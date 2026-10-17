package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestOriginMismatchDiagnosticIsRedactedAndCounted(t *testing.T) {
	s := newSessionStore()
	h := gatewayHandlerStore(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(204) }), s)
	bootstrap := httptest.NewRequest("POST", prefix+"/gateway/session", nil)
	bootstrap.Header.Set("Origin", "https://private-nas.example:8443")
	bootstrap.Header.Set("X-Trim-Userid", "1000")
	bootstrap.Header.Set("X-Trim-Isadmin", "true")
	bootstrap.Header.Set("X-Fnos-Bootstrap", "1")
	b := httptest.NewRecorder()
	h.ServeHTTP(b, bootstrap)
	if b.Code != 200 {
		t.Fatalf("bootstrap=%d", b.Code)
	}
	cookie := b.Result().Cookies()[0]
	var payload map[string]any
	if json.Unmarshal(b.Body.Bytes(), &payload) != nil {
		t.Fatal("invalid bootstrap")
	}
	token := payload["token"].(string)
	r := httptest.NewRequest("GET", prefix+"/api/v2/app/preferences", nil)
	r.Header.Set("Origin", "https://other-private-nas.example:9443")
	r.Header.Set("Cookie", cookie.Name+"="+cookie.Value)
	r.Header.Set(csrfHeader, token)
	r.Header.Set("X-Trim-Userid", "1000")
	r.Header.Set("X-Trim-Isadmin", "true")
	out := httptest.NewRecorder()
	h.ServeHTTP(out, r)
	if out.Code != 403 {
		t.Fatalf("status=%d", out.Code)
	}
	if strings.Contains(out.Body.String(), "private-nas") || strings.Contains(out.Body.String(), "other-private") || strings.Contains(out.Body.String(), "https://") {
		t.Fatalf("origin leaked: %s", out.Body.String())
	}
	var d map[string]any
	if err := json.Unmarshal(out.Body.Bytes(), &d); err != nil {
		t.Fatal(err)
	}
	if d["reason"] != "session_origin_mismatch" || d["bootstrap_origin_changed"] != true {
		t.Fatalf("diagnostic=%v", d)
	}
	if d["session_origin_fingerprint"] == nil || d["request_origin_fingerprint"] == nil {
		t.Fatalf("fingerprints missing: %v", d)
	}
	if s.originMismatchCount() != 1 {
		t.Fatalf("count=%d", s.originMismatchCount())
	}
}

func TestOriginFingerprintDoesNotExposeAuthority(t *testing.T) {
	fp := originFingerprint("https://secret.example:443")
	if len(fp) != 12 || strings.Contains(fp, "secret") {
		t.Fatalf("fp=%q", fp)
	}
	if originPortClass("http://a.example") != "http-default" || originPortClass("https://a.example:8443") != "https-nondefault" {
		t.Fatal("port class")
	}
}
