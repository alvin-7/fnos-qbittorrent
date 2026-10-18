package main

import (
	"context"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"unsafe"
)

// A private namespace exercises real tmpfs child mounts, not forged mount IDs.
func TestDirectoryNestedMountExpansion(t *testing.T) {
	root := os.Getenv("DIRECTORY_MOUNT_FIXTURE")
	if root == "" {
		root = t.TempDir()
		os.Mkdir(filepath.Join(root, "mounted"), 0700)
		os.Mkdir(filepath.Join(root, "bound"), 0700)
		exe, _ := os.Executable()
		cmd := exec.Command("unshare", "-Urnm", "sh", "-c", `mount -t tmpfs tmpfs "$1/mounted" && mount --bind "$1/mounted" "$1/bound" && exec "$2" -test.run '^TestDirectoryNestedMountExpansion$' -test.v`, "fixture", root, exe)
		cmd.Env = append(os.Environ(), "DIRECTORY_MOUNT_FIXTURE="+root, "GORACE=atexit_sleep_ms=0")
		out, err := cmd.CombinedOutput()
		if err != nil {
			t.Fatalf("namespace regression failed: %v\n%s", err, out)
		}
		t.Log(string(out))
		return
	}
	// tmpfs and bind mounts have different mount IDs; both are ordinary
	// authorized descendants, including a bind with the same device identity.
	if err := os.Mkdir(filepath.Join(root, "mounted", "ordinary"), 0700); err != nil {
		t.Fatal(err)
	}
	s := newDirectoryService(&mockDirectoryProvider{paths: []string{root}})
	roots, _, err := s.roots(context.Background(), "1000")
	if err != nil || len(roots) != 1 {
		t.Fatal("roots", err)
	}
	for _, rel := range []string{"", "mounted", "bound"} {
		w := directoryCall(s, "browse", map[string]any{"rootId": roots[0].RootID, "relativePath": rel})
		var d struct{ Entries []directoryEntry }
		json.Unmarshal(w.Body.Bytes(), &d)
		want := 1
		if rel == "" {
			want = 2
		}
		if w.Code != 200 || len(d.Entries) != want {
			t.Fatalf("root succeeds but child mount cannot expand: relative=%q status=%d %s", rel, w.Code, w.Body.String())
		}
	}
}

func TestDirectoryFilteredIsNotEmpty(t *testing.T) {
	root := t.TempDir()
	s := newDirectoryService(&mockDirectoryProvider{paths: []string{root}})
	roots, _, err := s.roots(context.Background(), "1000")
	if err != nil {
		t.Fatal(err)
	}
	check := func(reason string) {
		t.Helper()
		w := directoryCall(s, "browse", map[string]any{"rootId": roots[0].RootID})
		var d struct {
			Reason      string
			Diagnostics directoryDiagnostic
		}
		json.Unmarshal(w.Body.Bytes(), &d)
		if w.Code != 200 || d.Reason != reason || d.Diagnostics.Stage != "browse_children" {
			t.Fatalf("missing safe empty/filter distinction: %d %s", w.Code, w.Body.String())
		}
		if strings.Contains(w.Body.String(), "denied-child") {
			t.Fatal("filtered name leaked")
		}
	}
	check("DIRECTORY_EMPTY")
	os.Mkdir(filepath.Join(root, "denied-child"), 0700)
	s.provider.(*mockDirectoryProvider).denied = filepath.Join(root, "denied-child")
	check("DIRECTORY_CHILDREN_FILTERED")
}

func TestDirectoryUnknownDirentAndReadErrors(t *testing.T) {
	root := t.TempDir()
	os.Mkdir(filepath.Join(root, "ordinary"), 0700)
	unknown := func(fd int, b []byte) (int, error) {
		n, e := syscall.ReadDirent(fd, b)
		for pos := 0; pos < n; {
			d := (*syscall.Dirent)(unsafe.Pointer(&b[pos]))
			d.Type = syscall.DT_UNKNOWN
			pos += int(d.Reclen)
		}
		return n, e
	}
	got := directoryWorkRead(workerRequest{Root: root, List: true}, unknown)
	if got.Error != "" || len(got.Entries) != 1 || got.Entries[0] != "ordinary" {
		t.Fatalf("DT_UNKNOWN must use authoritative openat: %+v", got)
	}
	for _, errno := range []syscall.Errno{syscall.EACCES, syscall.EIO, syscall.ESTALE} {
		got = directoryWorkRead(workerRequest{Root: root, List: true}, func(int, []byte) (int, error) { return 0, errno })
		if got.Error != directoryFilesystemReason(errno) {
			t.Fatalf("errno swallowed: %+v", got)
		}
	}
}

func TestDirectoryMultiFilesystemRootsAndDenial(t *testing.T) {
	a := t.TempDir()
	b, err := os.MkdirTemp("/dev/shm", "directory-regression-")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(b)
	for _, root := range []string{a, b} {
		os.Mkdir(filepath.Join(root, "中文 space"), 0700)
	}
	var sa, sb syscall.Statfs_t
	syscall.Statfs(a, &sa)
	syscall.Statfs(b, &sb)
	if sa.Type == sb.Type {
		t.Fatal("fixture must exercise different filesystems")
	}
	s := newDirectoryService(&mockDirectoryProvider{paths: []string{a, b}})
	roots, _, err := s.roots(context.Background(), "1000")
	if err != nil || len(roots) != 2 {
		t.Fatal(err)
	}
	for _, r := range roots {
		w := directoryCall(s, "browse", map[string]any{"rootId": r.RootID})
		if w.Code != 200 || !strings.Contains(w.Body.String(), "中文 space") {
			t.Fatal(w.Code, w.Body.String())
		}
	}
	denied := filepath.Join(b, "blocked")
	os.Mkdir(denied, 0000)
	defer os.Chmod(denied, 0700)
	w := directoryCall(s, "browse", map[string]any{"rootId": roots[1].RootID, "relativePath": "blocked"})
	if w.Code != 404 || !strings.Contains(w.Body.String(), "package_read_denied") || strings.Contains(w.Body.String(), denied) {
		t.Fatal("unsafe/missing errno diagnostics", w.Code, w.Body.String())
	}
}
