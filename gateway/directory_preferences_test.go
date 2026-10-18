package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"strings"
	"testing"
)

func TestDirectoryPreferenceChangesDoNotInspectExistingTasks(t *testing.T) {
	root := t.TempDir()
	for _, tc := range []struct {
		name    string
		prefs   map[string]any
		enabled bool
		allowed bool
	}{
		{"default", map[string]any{"save_path": root}, false, true},
		{"enabled temporary", map[string]any{"temp_path_enabled": true, "temp_path": root}, false, true},
		{"disabled temporary", map[string]any{"temp_path_enabled": false, "temp_path": ""}, true, true},
		{"temporary only enabled", map[string]any{"temp_path": root}, true, true},
		{"temporary only disabled", map[string]any{"temp_path": ""}, false, true},
		{"invalid default", map[string]any{"save_path": ""}, false, false},
		{"unauthorized default", map[string]any{"save_path": root + "/missing"}, false, false},
		{"invalid enabled temporary", map[string]any{"temp_path_enabled": true, "temp_path": ""}, false, false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			s := newDirectoryService(&mockDirectoryProvider{paths: []string{root}})
			next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
				if strings.HasSuffix(r.URL.Path, "/torrents/info") {
					t.Fatal("preferences must not query existing tasks")
				}
				if !strings.HasSuffix(r.URL.Path, "/app/preferences") {
					t.Fatalf("unexpected upstream read: %s", r.URL.Path)
				}
				json.NewEncoder(w).Encode(map[string]any{"temp_path_enabled": tc.enabled})
			})
			b, _ := json.Marshal(tc.prefs)
			r := httptest.NewRequest("POST", prefix+"/api/v2/app/setPreferences", strings.NewReader(url.Values{"json": {string(b)}}.Encode()))
			r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
			r.Header.Set("X-Trim-Userid", "1000")
			w := httptest.NewRecorder()
			if got := s.guard(next, w, r); got != tc.allowed {
				t.Fatalf("allowed=%v status=%d body=%s", got, w.Code, w.Body.String())
			}
		})
	}
}

func TestDirectoryCategoryAutoTMMSafetyRemains(t *testing.T) {
	s := newDirectoryService(&mockDirectoryProvider{})
	next := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode([]map[string]any{{"category": "fixture", "auto_tmm": true}})
	})
	r := httptest.NewRequest("POST", prefix+"/api/v2/torrents/editCategory", strings.NewReader("category=fixture"))
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	if s.guard(next, w, r) || w.Code != 409 || !strings.Contains(w.Body.String(), "PATH_CHANGE_RISK") {
		t.Fatalf("category safety lost: %d %s", w.Code, w.Body.String())
	}
}
