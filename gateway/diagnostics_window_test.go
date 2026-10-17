package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestDiagnosticWindow(t *testing.T) {
	logs := `[]`
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { io.WriteString(w, logs) }))
	defer server.Close()
	tr := &nativeTransport{base: http.DefaultTransport, backend: server.URL}
	req := httptest.NewRequest("GET", "http://local/api/v2/diagnostics/add", nil)
	r := tr.addDiagnostics(req)
	var start map[string]any
	json.NewDecoder(r.Body).Decode(&start)
	key := start["cursor"].(string)
	for _, input := range []string{`[]`, fmt.Sprintf(`[{"id":1,"timestamp":%d,"type":4,"message":"SECRET unrelated"}]`, time.Now().Unix()-30)} {
		logs = input
		r = tr.addDiagnostics(httptest.NewRequest("GET", "http://local/api/v2/diagnostics/add?cursor="+key, nil))
		var v struct{ Events []safeAddLog }
		json.NewDecoder(r.Body).Decode(&v)
		if len(v.Events) != 0 {
			t.Fatal("old logs leaked")
		}
	}
	logs = fmt.Sprintf(`[{"id":2,"timestamp":%d,"type":4,"message":"Failed to download torrent. Source: SECRET. Reason: Host not found"}]`, time.Now().Unix())
	r = tr.addDiagnostics(httptest.NewRequest("GET", "http://local/api/v2/diagnostics/add?cursor="+key, nil))
	b, _ := io.ReadAll(r.Body)
	if !strings.Contains(string(b), "DNS_LOOKUP_FAILED") || strings.Contains(string(b), "SECRET") {
		t.Fatal("window/classification failed")
	}
	for _, target := range []string{"http://local/api/v2/diagnostics/add?url=SECRET", "http://local/api/v2/diagnostics/add?cursor=a&cursor=b"} {
		if tr.addDiagnostics(httptest.NewRequest("GET", target, nil)).StatusCode != 400 {
			t.Fatal("query allowed")
		}
	}
	if tr.addDiagnostics(httptest.NewRequest("POST", "http://local/api/v2/diagnostics/add", nil)).StatusCode != 405 {
		t.Fatal("mutation allowed")
	}
}
