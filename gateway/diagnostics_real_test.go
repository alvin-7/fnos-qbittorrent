package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"testing"
	"time"
)

type diagnosticTestTransport struct{}

func (diagnosticTestTransport) RoundTrip(r *http.Request) (*http.Response, error) {
	r.Host = r.URL.Host
	return http.DefaultTransport.RoundTrip(r)
}
func TestRealDiagnosticAcquisition(t *testing.T) {
	backend := os.Getenv("DIAGNOSTIC_TEST_BACKEND")
	if backend == "" {
		t.Skip("isolated backend not configured")
	}
	tr := &nativeTransport{base: diagnosticTestTransport{}, backend: backend, cookie: os.Getenv("DIAGNOSTIC_TEST_COOKIE")}
	source := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasPrefix(r.URL.Path, "/404") {
			w.WriteHeader(404)
			return
		}
		w.Write([]byte("<html>controlled not torrent</html>"))
	}))
	defer source.Close()
	for _, c := range []struct{ path, category string }{{"/404?passkey=SYNTHETIC_SECRET", "HTTP"}, {"/html?token=SYNTHETIC_SECRET", "INVALID_TORRENT"}} {
		start := tr.addDiagnostics(httptest.NewRequest("GET", "http://local/api/v2/diagnostics/add", nil))
		var st map[string]any
		json.NewDecoder(start.Body).Decode(&st)
		key, ok := st["cursor"].(string)
		if !ok {
			t.Fatal("baseline unavailable")
		}
		form := url.Values{"urls": {source.URL + c.path}, "savepath": {os.Getenv("DIAGNOSTIC_TEST_SAVE")}}.Encode()
		r, _ := http.NewRequest("POST", backend+"/api/v2/torrents/add", strings.NewReader(form))
		r.Host = "127.0.0.1:18080"
		r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		res, e := tr.RoundTrip(r)
		if e != nil {
			t.Fatal("add failed")
		}
		io.Copy(io.Discard, res.Body)
		res.Body.Close()
		found := false
		for i := 0; i < 40; i++ {
			time.Sleep(250 * time.Millisecond)
			res := tr.addDiagnostics(httptest.NewRequest("GET", "http://local/api/v2/diagnostics/add?cursor="+key, nil))
			b, _ := io.ReadAll(res.Body)
			if strings.Contains(string(b), "SYNTHETIC_SECRET") || strings.Contains(string(b), source.URL) {
				t.Fatal("privacy breach")
			}
			var d struct{ Events []safeAddLog }
			json.Unmarshal(b, &d)
			for _, v := range d.Events {
				if v.Category == c.category {
					found = true
				}
			}
			if found {
				break
			}
		}
		if !found {
			logs, _ := tr.readDiagnosticLogs(httptest.NewRequest("GET", "http://local/", nil))
			for _, l := range logs {
				low := strings.ToLower(l.Message)
				fmt.Println("safe classification", classifyAddLog(l).Category, "http404", strings.Contains(low, "404"), "status", strings.Contains(low, "status"), "error", strings.Contains(low, "error"), "qt", strings.Contains(low, "contentnotfound"))
				fmt.Printf("safe signature flags type=%d torrent=%v failed=%v download=%v reason=%v notfound=%v bencode=%v invalid=%v\\n", l.Type, strings.Contains(low, "torrent"), strings.Contains(low, "failed"), strings.Contains(low, "download"), strings.Contains(low, "reason:"), strings.Contains(low, "not found"), strings.Contains(low, "bencod"), strings.Contains(low, "invalid"))
			}
			t.Fatalf("controlled %s classification absent (raw logs suppressed)", c.category)
		}
		fmt.Println("controlled real qB classification:", c.category, "safe output verified")
	}
}
