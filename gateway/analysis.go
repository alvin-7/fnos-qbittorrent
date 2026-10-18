package main

// Site analysis is a management-only projection, never a raw Tracker response.
import (
	"context"
	"encoding/json"
	"net/http"
	"net/url"
	"sort"
	"strings"
	"sync"
	"time"
)

type siteStat struct {
	Name        string   `json:"name"`
	Hashes      []string `json:"hashes"`
	LogicalSize int64    `json:"logicalSize"`
}
type siteSnapshot struct {
	Eligible       []siteStat `json:"eligible"`
	Running        []siteStat `json:"running"`
	EligibleHashes []string   `json:"eligibleHashes"`
	RunningHashes  []string   `json:"runningHashes"`
}
type siteAnalysis struct {
	upstream http.Handler
	mu       sync.Mutex
	expires  time.Time
	cached   siteSnapshot
	slots    chan struct{}
}

func newSiteAnalysis(h http.Handler) *siteAnalysis {
	return &siteAnalysis{upstream: h, slots: make(chan struct{}, 4)}
}
func analysisRead(h http.Handler, r *http.Request, route string, out any) bool {
	q := r.Clone(r.Context())
	q.URL = &url.URL{Path: prefix + "/api/v2/" + strings.SplitN(route, "?", 2)[0]}
	if p := strings.SplitN(route, "?", 2); len(p) == 2 {
		q.URL.RawQuery = p[1]
	}
	q.Method = "GET"
	q.Body = nil
	q.ContentLength = 0
	q.Form = nil
	q.PostForm = nil
	q.MultipartForm = nil
	q.Header = r.Header.Clone()
	q.Header.Del("Accept-Encoding")
	q.Header.Del("Content-Type")
	res := &connectorResponse{header: make(http.Header)}
	h.ServeHTTP(res, q)
	return !res.overflow && (res.code == 0 || res.code == 200) && json.Unmarshal(res.body.Bytes(), out) == nil
}
func safeTrackerDomain(raw string) string {
	u, e := url.Parse(raw)
	if e != nil || (u.Scheme != "http" && u.Scheme != "https" && u.Scheme != "udp") || u.Hostname() == "" {
		return ""
	}
	host := strings.ToLower(u.Hostname())
	if strings.ContainsAny(host, " /\\\r\n\t@") || len(host) > 253 {
		return ""
	}
	for _, c := range host {
		if !(c >= 'a' && c <= 'z' || c >= '0' && c <= '9' || c == '.' || c == '-' || c == ':') {
			return ""
		}
	}
	return host
}
func (s *siteAnalysis) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	if r.Method != "GET" || r.URL.RawQuery != "" {
		w.WriteHeader(405)
		return
	}
	// Single flight prevents concurrent visitors multiplying upstream fan-out.
	s.mu.Lock()
	defer s.mu.Unlock()
	if time.Now().Before(s.expires) {
		json.NewEncoder(w).Encode(s.cached)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()
	r = r.WithContext(ctx)
	var tasks []struct {
		Hash     string  `json:"hash"`
		State    string  `json:"state"`
		Progress float64 `json:"progress"`
		Size     int64   `json:"size"`
	}
	if !analysisRead(s.upstream, r, "torrents/info", &tasks) {
		w.WriteHeader(503)
		json.NewEncoder(w).Encode(map[string]string{"code": "ANALYSIS_SOURCE_UNAVAILABLE"})
		return
	}
	type row struct {
		hash    string
		size    int64
		running bool
		sites   []string
	}
	rows := []row{}
	seen := map[string]bool{}
	for _, t := range tasks {
		if seen[t.Hash] || len(t.Hash) != 40 || strings.Trim(t.Hash, "0123456789abcdefABCDEF") != "" || t.Progress < 1 {
			continue
		}
		running := t.State == "uploading" || t.State == "stalledUP" || t.State == "forcedUP"
		if !running && t.State != "stoppedUP" && t.State != "pausedUP" && t.State != "queuedUP" {
			continue
		}
		seen[t.Hash] = true
		rows = append(rows, row{hash: t.Hash, size: t.Size, running: running})
	}
	// is_private is supplied by properties, NOT by torrents/info. Missing/failed
	// metadata remains unknown rather than pretending a public task is private.
	var wg sync.WaitGroup
	for i := range rows {
		select {
		case s.slots <- struct{}{}:
		case <-ctx.Done():
			rows[i].sites = []string{"unknown"}
			continue
		}
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			defer func() { <-s.slots }()
			var prop struct {
				Private *bool `json:"private"`
			}
			if !analysisRead(s.upstream, r, "torrents/properties?hash="+rows[i].hash, &prop) || prop.Private == nil {
				rows[i].sites = []string{"unknown"}
				return
			}
			if !*prop.Private {
				return
			}
			var trackers []struct {
				URL string `json:"url"`
			}
			domains := map[string]bool{}
			if analysisRead(s.upstream, r, "torrents/trackers?hash="+rows[i].hash, &trackers) {
				for _, t := range trackers {
					if d := safeTrackerDomain(t.URL); d != "" {
						domains[d] = true
					}
				}
			}
			for d := range domains {
				rows[i].sites = append(rows[i].sites, d)
			}
			if len(rows[i].sites) == 0 {
				rows[i].sites = []string{"unknown"}
			}
		}(i)
	}
	wg.Wait()
	eligible, running := map[string]*siteStat{}, map[string]*siteStat{}
	result := siteSnapshot{Eligible: []siteStat{}, Running: []siteStat{}, EligibleHashes: []string{}, RunningHashes: []string{}}
	for _, r := range rows {
		if len(r.sites) == 0 {
			continue
		}
		result.EligibleHashes = append(result.EligibleHashes, r.hash)
		if r.running {
			result.RunningHashes = append(result.RunningHashes, r.hash)
		}
		for _, domain := range r.sites {
			for j, m := range []map[string]*siteStat{eligible, running} {
				if j == 1 && !r.running {
					continue
				}
				v := m[domain]
				if v == nil {
					v = &siteStat{Name: domain, Hashes: []string{}}
					m[domain] = v
				}
				v.Hashes = append(v.Hashes, r.hash)
				if r.size > 0 {
					v.LogicalSize += r.size
				}
			}
		}
	}
	for _, v := range eligible {
		sort.Strings(v.Hashes)
		result.Eligible = append(result.Eligible, *v)
	}
	for _, v := range running {
		sort.Strings(v.Hashes)
		result.Running = append(result.Running, *v)
	}
	sort.Slice(result.Eligible, func(i, j int) bool { return result.Eligible[i].Name < result.Eligible[j].Name })
	sort.Slice(result.Running, func(i, j int) bool { return result.Running[i].Name < result.Running[j].Name })
	sort.Strings(result.EligibleHashes)
	sort.Strings(result.RunningHashes)
	s.cached = result
	s.expires = time.Now().Add(30 * time.Second)
	json.NewEncoder(w).Encode(result)
}
