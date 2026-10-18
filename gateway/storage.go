package main

import (
	"context"
	"encoding/json"
	"net/http"
 "os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type storageVolume struct {
	ID             string   `json:"id"`
	DisplayName    string   `json:"displayName"`
	Roots          []string `json:"roots"`
	Status         string   `json:"status"`
	TotalBytes     *uint64  `json:"totalBytes,omitempty"`
	FreeBytes      *uint64  `json:"freeBytes,omitempty"`
	AvailableBytes *uint64  `json:"availableBytes,omitempty"`
	UsedBytes      *uint64  `json:"usedBytes,omitempty"`
}

func (s *directoryService) storage(w http.ResponseWriter, r *http.Request) {
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	uid := r.Header.Get("X-Trim-Userid")
	paths, e := s.provider.Roots(ctx)
	if e != nil {
		directoryError(w, e)
		return
	}
	paths = append([]string(nil), paths...)
	for _, path := range strings.Split(os.Getenv("TRIM_DATA_SHARE_PATHS"), ":") {
		if path != "" { paths = append(paths, path) }
	}
	if len(paths) > 128 {
		directoryError(w, errSource)
		return
	}
	volumes := map[string]*storageVolume{}
	seen := map[string]bool{}
	for _, path := range paths {
		if !directorySafe(path, true) || path == "/" {
			directoryError(w, errSource)
			return
		}
		path = filepath.Clean(path)
		if seen[path] || directoryPrivate(path) {
			continue
		}
		seen[path] = true
		acl, e := s.provider.ACL(ctx, uid, []string{path})
		if e != nil {
			directoryError(w, e)
			return
		}
		if len(acl) != 1 || acl[0].Path != path {
			directoryError(w, errSource)
			return
		}
		if !acl[0].Readable {
			continue
		}
		data, e := s.worker(ctx, workerRequest{Root: path})
		id := "unknown:" + directoryHash(path)
		status := "unknown"
		if e == nil {
			s.mu.Lock()
			old, known := s.identities[path]
			if !known {
				s.identities[path] = data.Identity
			}
			s.mu.Unlock()
			if !known || old == data.Identity {
				id = directoryHash(data.VolumeIdentity)
				status = "ready"
			}
		}
		v := volumes[id]
		if v == nil {
			v = &storageVolume{ID: id, DisplayName: filepath.Base(path), Roots: []string{}, Status: status}
			if status == "ready" {
				used := data.TotalBytes - data.FreeBytes
				v.TotalBytes = &data.TotalBytes
				v.FreeBytes = &data.FreeBytes
				v.AvailableBytes = &data.AvailableBytes
				v.UsedBytes = &used
			}
			volumes[id] = v
		}
		v.Roots = append(v.Roots, path)
	}
	out := []storageVolume{}
	for _, v := range volumes {
		sort.Strings(v.Roots)
		out = append(out, *v)
	}
	sort.Slice(out, func(i, j int) bool { return strings.Compare(out[i].ID, out[j].ID) < 0 })
	json.NewEncoder(w).Encode(map[string]any{"volumes": out})
}
