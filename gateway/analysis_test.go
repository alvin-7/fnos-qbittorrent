package main

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"sync/atomic"
	"testing"
	"time"
)

func TestAnalysisSafeSites(t *testing.T) {
	var calls, active, peak int32
	upstream := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "torrents/info") {
			fmt.Fprint(w, `[{"hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","state":"stalledUP","progress":1,"size":12},{"hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","state":"stoppedUP","progress":1,"size":20}]`)
			return
		}
		if strings.HasSuffix(r.URL.Path, "torrents/properties") {
			fmt.Fprint(w, `{"private":true}`)
			return
		}
		atomic.AddInt32(&calls, 1)
		n := atomic.AddInt32(&active, 1)
		for p := atomic.LoadInt32(&peak); n > p && !atomic.CompareAndSwapInt32(&peak, p, n); p = atomic.LoadInt32(&peak) {
		}
		defer atomic.AddInt32(&active, -1)
		time.Sleep(time.Millisecond)
		fmt.Fprint(w, `[{"url":"https://user:secret@Tracker.Example/private-passkey/announce?token=sensitive"},{"url":"https://tracker.example/duplicate"},{"url":"** [DHT] **"}]`)
	})
	s := newSiteAnalysis(upstream)
	r := httptest.NewRequest("GET", prefix+"/api/v2/gateway/analysis/sites", nil)
	for i := 0; i < 2; i++ {
		w := httptest.NewRecorder()
		s.ServeHTTP(w, r)
		if w.Code != 200 {
			t.Fatal(w.Code, w.Body.String())
		}
		text := w.Body.String()
		if strings.Contains(text, "secret") || strings.Contains(text, "passkey") || strings.Contains(text, "sensitive") || strings.Contains(text, "https") || strings.Contains(text, "DHT") {
			t.Fatal(text)
		}
		var result siteSnapshot
		if json.Unmarshal(w.Body.Bytes(), &result) != nil || len(result.Eligible) != 1 || result.Eligible[0].LogicalSize != 32 || len(result.Eligible[0].Hashes) != 2 || len(result.Running[0].Hashes) != 1 {
			t.Fatal(text)
		}
	}
	if calls != 2 || peak > 4 {
		t.Fatal(calls, peak)
	}
	s.expires = time.Time{}
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	if calls != 4 {
		t.Fatal("TTL did not expire", calls)
	}
}
func TestStorageDeduplicatesAndRevokes(t *testing.T) {
	root := t.TempDir()
	a, b := filepath.Join(root, "a"), filepath.Join(root, "b")
	os.Mkdir(a, 0700)
	os.Mkdir(b, 0700)
	p := &mockDirectoryProvider{paths: []string{a, b}}
	s := newDirectoryService(p)
	w := directoryCall(s, "storage", map[string]any{})
	var out struct{ Volumes []storageVolume }
	if w.Code != 200 || json.Unmarshal(w.Body.Bytes(), &out) != nil || len(out.Volumes) != 1 || len(out.Volumes[0].Roots) != 2 || out.Volumes[0].TotalBytes == nil || *out.Volumes[0].TotalBytes == 0 {
		t.Fatal(w.Code, w.Body.String())
	}
	id := out.Volumes[0].ID
	p.paths = []string{b}
	w = directoryCall(s, "storage", map[string]any{})
	json.Unmarshal(w.Body.Bytes(), &out)
	if len(out.Volumes) != 1 || out.Volumes[0].ID != id || len(out.Volumes[0].Roots) != 1 {
		t.Fatal(w.Body.String())
	}
	os.Remove(b)
	w = directoryCall(s, "storage", map[string]any{})
	if w.Code != 200 || !strings.Contains(w.Body.String(), "unknown") || strings.Contains(w.Body.String(), "totalBytes") {
		t.Fatal(w.Code, w.Body.String())
	}
	p.paths = nil
	w = directoryCall(s, "storage", map[string]any{})
	if w.Code != 200 || !strings.Contains(w.Body.String(), `"volumes":[]`) {
		t.Fatal(w.Code, w.Body.String())
	}
	_ = context.Background()
}
