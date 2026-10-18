package main

import (
	"bytes"
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

// Business writes recheck current fnOS grants/ACL; picker choices are never tokens.
// Existing tasks make path preference changes fail closed rather than risk moves.
func (s *directoryService) guard(next http.Handler, w http.ResponseWriter, r *http.Request) bool {
	route := strings.TrimPrefix(r.URL.Path, prefix+"/api/v2/")
	if route != "torrents/add" && route != "app/setPreferences" && route != "torrents/createCategory" && route != "torrents/editCategory" {
		return true
	}
	if r.Method != "POST" {
		directoryError(w, errDirectory)
		return false
	}
	body, e := io.ReadAll(io.LimitReader(r.Body, (16<<20)+1))
	if e != nil || len(body) > 16<<20 {
		w.WriteHeader(413)
		return false
	}
	r.Body = io.NopCloser(bytes.NewReader(body))
	parsed := r.Clone(r.Context())
	parsed.Body = io.NopCloser(bytes.NewReader(body))
	if strings.HasPrefix(r.Header.Get("Content-Type"), "multipart/") {
		e = parsed.ParseMultipartForm(16 << 20)
		if parsed.MultipartForm != nil {
			defer parsed.MultipartForm.RemoveAll()
		}
	} else {
		e = parsed.ParseForm()
	}
	if e != nil {
		w.WriteHeader(400)
		return false
	}
	r.Body = io.NopCloser(bytes.NewReader(body))
	read := func(route string, out any) bool {
		q := r.Clone(r.Context())
		u, _ := url.Parse(prefix + "/api/v2/" + route)
		q.URL = u
		q.Method = "GET"
		q.Body = nil
		q.ContentLength = 0
		q.Form = nil
		q.PostForm = nil
		q.MultipartForm = nil
		q.Header = r.Header.Clone()
		q.Header.Del("Content-Type")
  q.Header.Del("Accept-Encoding")
		result := &connectorResponse{header: make(http.Header)}
		next.ServeHTTP(result, q)
		return !result.overflow && (result.code == 200 || result.code == 0) && json.Unmarshal(result.body.Bytes(), out) == nil
	}
	paths := []string{}
	var prefs map[string]json.RawMessage
	if route == "app/setPreferences" {
		if len(parsed.PostForm["json"]) != 1 || json.Unmarshal([]byte(parsed.PostForm.Get("json")), &prefs) != nil {
			w.WriteHeader(400)
			return false
		}
		changed := false
		var current map[string]json.RawMessage
		for _, key := range []string{"save_path", "temp_path", "temp_path_enabled"} {
			if raw, ok := prefs[key]; ok {
				if current == nil && !read("app/preferences", &current) {
					directoryError(w, errSource)
					return false
				}
				if !bytes.Equal(raw, current[key]) {
					changed = true
				}
				if key != "temp_path_enabled" {
					var p string
					if json.Unmarshal(raw, &p) != nil || p == "" {
						directoryError(w, errDirectory)
						return false
					}
					paths = append(paths, p)
				}
			}
		}
		if changed {
			var tasks []json.RawMessage
			if !read("torrents/info", &tasks) || len(tasks) > 0 {
				w.WriteHeader(409)
				json.NewEncoder(w).Encode(map[string]string{"code": "PATH_CHANGE_RISK"})
				return false
			}
		}
	} else if route == "torrents/add" {
		if len(parsed.Form["savepath"]) != 1 {
			directoryError(w, errDirectory)
			return false
		}
		paths = append(paths, parsed.Form.Get("savepath"))
		// Category/automatic management could override the explicitly selected path.
		var current struct {
			TempEnabled bool   `json:"temp_path_enabled"`
			Temp        string `json:"temp_path"`
			Save        string `json:"save_path"`
		}
		if !read("app/preferences", &current) {
			directoryError(w, errSource)
			return false
		}
		if current.TempEnabled {
			paths = append(paths, current.Temp)
		}
		if cat := parsed.Form.Get("category"); cat != "" {
			var cats map[string]struct {
				Save string `json:"savePath"`
			}
			if !read("torrents/categories", &cats) {
				directoryError(w, errSource)
				return false
			}
			if v, ok := cats[cat]; ok && v.Save != "" {
				paths = append(paths, v.Save)
			}
		}
	} else {
		if len(parsed.Form["savePath"]) > 1 {
			w.WriteHeader(400)
			return false
		}
		if p := parsed.Form.Get("savePath"); p != "" {
			paths = append(paths, p)
		}
		var tasks []struct {
			Category string `json:"category"`
			Auto     bool   `json:"auto_tmm"`
		}
		if !read("torrents/info", &tasks) {
			directoryError(w, errSource)
			return false
		}
		for _, t := range tasks {
			if t.Auto && t.Category == parsed.Form.Get("category") {
				w.WriteHeader(409)
				json.NewEncoder(w).Encode(map[string]string{"code": "PATH_CHANGE_RISK"})
				return false
			}
		}
	}
	if len(paths) == 0 {
		return true
	}
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	uid := r.Header.Get("X-Trim-Userid")
	roots, _, e := s.roots(ctx, uid)
	if e != nil {
		directoryError(w, e)
		return false
	}
	for _, p := range paths {
		c, e := s.checked(ctx, uid, p, roots, "")
		if e != nil {
			directoryError(w, e)
			return false
		}
		if !c.Writable {
			w.WriteHeader(422)
			json.NewEncoder(w).Encode(map[string]string{"code": "READ_ONLY"})
			return false
		}
	}
	return true
}
