package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDirectoryRelativeTraverseOnlyIntermediate(t *testing.T) {
	root := t.TempDir()
	parent := filepath.Join(root, "traverse")
	leaf := filepath.Join(parent, "leaf")
	if e := os.MkdirAll(leaf, 0700); e != nil {
		t.Fatal(e)
	}
	if e := os.Chmod(parent, 0111); e != nil {
		t.Fatal(e)
	}
	defer os.Chmod(parent, 0700)
	if _, e := os.ReadDir(parent); !os.IsPermission(e) {
		t.Fatal("fixture must deny read")
	}
	s := newDirectoryService(&mockDirectoryProvider{paths: []string{root}})
	roots, _, e := s.roots(context.Background(), "1000")
	if e != nil {
		t.Fatal(e)
	}
	w := directoryCall(s, "browse", map[string]any{"rootId": roots[0].RootID, "relativePath": "traverse/leaf"})
	if w.Code != 200 {
		t.Fatalf("execute-only intermediate must not block readable authorized leaf: %s", w.Body.String())
	}
}

func TestDirectoryDenialOriginCounts(t *testing.T) {
	for _, tc := range []struct {
		name, reason string
		mode         os.FileMode
		acl, link    bool
	}{
		{"os-denied", "PACKAGE_OPEN_EACCES", 0000, false, false},
		{"execute-only-final", "PACKAGE_OPEN_EACCES", 0111, false, false},
		{"api-denied", "ACL_API_DENIED", 0700, true, false},
		{"link", "SYMLINK_REJECTED", 0700, false, true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			root := t.TempDir()
			child := filepath.Join(root, "secret-rejected-child")
			if tc.link {
				if e := os.Symlink(root, child); e != nil {
					t.Fatal(e)
				}
			} else {
				if e := os.Mkdir(child, tc.mode); e != nil {
					t.Fatal(e)
				}
				defer os.Chmod(child, 0700)
			}
			p := &mockDirectoryProvider{paths: []string{root}}
			if tc.acl {
				p.denied = child
			}
			s := newDirectoryService(p)
			roots, _, e := s.roots(context.Background(), "1000")
			if e != nil {
				t.Fatal(e)
			}
			w := directoryCall(s, "browse", map[string]any{"rootId": roots[0].RootID})
			var d struct {
				Entries     []directoryEntry
				Diagnostics directoryDiagnostic
			}
			json.Unmarshal(w.Body.Bytes(), &d)
			if w.Code != 200 || len(d.Entries) != 0 || d.Diagnostics.Counts[tc.reason] != 1 {
				t.Fatalf("missing exact denial origin %s: %s", tc.reason, w.Body.String())
			}
			if strings.Contains(w.Body.String(), "secret-rejected-child") {
				t.Fatal("rejected name disclosed")
			}
		})
	}
}
