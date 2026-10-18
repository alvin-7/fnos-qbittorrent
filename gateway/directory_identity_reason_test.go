package main

import (
	"context"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

func TestDirectoryRootIdentityReason(t *testing.T) {
	root := filepath.Join(t.TempDir(), "grant")
	if e := os.Mkdir(root, 0700); e != nil {
		t.Fatal(e)
	}
	s := newDirectoryService(&mockDirectoryProvider{paths: []string{root}})
	if _, _, e := s.roots(context.Background(), "1000"); e != nil {
		t.Fatal(e)
	}
	if e := os.Rename(root, root+"-old"); e != nil {
		t.Fatal(e)
	}
	if e := os.Mkdir(root, 0700); e != nil {
		t.Fatal(e)
	}
	w := directoryCall(s, "roots", map[string]any{})
	var d struct {
		Code        string
		Diagnostics directoryDiagnostic
	}
	json.Unmarshal(w.Body.Bytes(), &d)
	if d.Code != "AUTH_MOUNT_REJECTED" || d.Diagnostics.Counts["MOUNT_REJECTED"] != 1 {
		t.Fatal(w.Body.String())
	}
}
