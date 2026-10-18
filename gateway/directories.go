package main

// Private fnOS download-directory service. Never infer grants from readable paths.
import (
	"bytes"
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
	"unicode/utf8"
	"unsafe"
)

const directoryApp = "fnos-qbittorrent-native"

// Linux O_PATH is not exposed by the old syscall package in every supported
// Go toolchain. Keep the platform constant local instead of weakening the
// traversal semantics for legacy builds.
const directoryOPath = 0x200000

var errDirectory = errors.New("DIRECTORY_UNAVAILABLE")
var errSource = errors.New("AUTH_SOURCE_UNAVAILABLE")

// Fixed, non-sensitive diagnostic codes; never include platform msg or paths.
type directorySourceError string

func (e directorySourceError) Error() string        { return string(e) }
func (e directorySourceError) Is(target error) bool { return target == errSource }
func sourceFailure(reason string) error             { return directorySourceError(reason) }

// Only fixed stage names and integer counts cross this diagnostic boundary.
// Paths, UID, platform messages and tokens are intentionally absent.
type directoryDiagnostic struct {
	Stage  string         `json:"stage"`
	Counts map[string]int `json:"counts"`
}
type directoryStageError struct {
	cause      error
	diagnostic directoryDiagnostic
}

func (e *directoryStageError) Error() string { return e.cause.Error() }
func (e *directoryStageError) Unwrap() error { return e.cause }
func directoryStage(cause error, stage string, counts map[string]int) error {
	return &directoryStageError{cause, directoryDiagnostic{stage, counts}}
}

type directoryACL struct {
	Path     string `json:"path"`
	Readable bool   `json:"readable"`
	Writable bool   `json:"writable"`
}
type directoryProvider interface {
	Roots(context.Context) ([]string, error)
	ACL(context.Context, string, []string) ([]directoryACL, error)
}
type fnosDirectoryProvider struct{ client *http.Client }

func newFnosDirectoryProvider() *fnosDirectoryProvider {
	return &fnosDirectoryProvider{&http.Client{Timeout: 2 * time.Second, Transport: &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{Timeout: time.Second}).DialContext(ctx, "unix", "/var/run/trim_open_gateway_apiscope.socket")
	}}}}
}
func (p *fnosDirectoryProvider) call(ctx context.Context, method string, data any, out any) error {
	token := os.Getenv("TRIM_API_TOKEN")
	if token == "" {
		return sourceFailure("AUTH_TOKEN_MISSING")
	}
	b, _ := json.Marshal(map[string]any{"appName": directoryApp, "req": method, "reqId": randomConnectorToken(), "data": data})
	r, _ := http.NewRequestWithContext(ctx, "POST", "http://localhost/api/v1/trimapp", bytes.NewReader(b))
	r.Header.Set("Content-Type", "application/json")
	r.Header.Set("Authorization", "Bearer "+token)
	res, e := p.client.Do(r)
	if e != nil {
		return errSource
	}
	defer res.Body.Close()
	var envelope struct {
		Code *int            `json:"code"`
		Data json.RawMessage `json:"data"`
	}
	if res.StatusCode == 401 {
		return sourceFailure("AUTH_TOKEN_REJECTED")
	}
	if res.StatusCode == 403 {
		return sourceFailure("AUTH_SCOPE_DENIED")
	}
	if res.StatusCode == 404 {
		return sourceFailure("AUTH_API_UNAVAILABLE")
	}
	if json.NewDecoder(io.LimitReader(res.Body, 1<<20)).Decode(&envelope) != nil || envelope.Code == nil {
		return sourceFailure("AUTH_RESPONSE_INVALID")
	}
	switch *envelope.Code {
	case 200004:
		return sourceFailure("AUTH_TOKEN_REJECTED")
	case 200003:
		return sourceFailure("AUTH_SCOPE_DENIED")
	case 200005:
		return sourceFailure("AUTH_API_UNAVAILABLE")
	case 200001:
		return sourceFailure("AUTH_REQUEST_INVALID")
	}
	if res.StatusCode != 200 || *envelope.Code != 0 {
		return errSource
	}
	if json.Unmarshal(envelope.Data, out) != nil {
		return sourceFailure("AUTH_RESPONSE_INVALID")
	}
	return nil
}
func (p *fnosDirectoryProvider) Roots(ctx context.Context) ([]string, error) {
	var d struct {
		Paths *[]string `json:"paths"`
	}
	if e := p.call(ctx, "trim.file.getSharedAccessibleFolders", map[string]any{}, &d); e != nil {
		return nil, e
	}
	if d.Paths == nil {
		return nil, sourceFailure("AUTH_RESPONSE_INVALID")
	}
	return *d.Paths, nil
}
func (p *fnosDirectoryProvider) ACL(ctx context.Context, uid string, paths []string) ([]directoryACL, error) {
	n, e := strconv.Atoi(uid)
	if e != nil {
		return nil, errSource
	}
	var a []directoryACL
	e = p.call(ctx, "trim.file.checkUserACL", map[string]any{"uid": n, "path": paths}, &a)
	return a, e
}

type directoryEntry struct {
	Name          string `json:"name"`
	RelativePath  string `json:"relativePath"`
	CanonicalPath string `json:"canonicalPath"`
	RootID        string `json:"rootId"`
	Writable      bool   `json:"writable"`
}
type directoryRoot struct {
	directoryEntry
	Source         []string `json:"source"`
	Status         string   `json:"status"`
	TotalBytes     uint64   `json:"totalBytes,omitempty"`
	FreeBytes      uint64   `json:"freeBytes,omitempty"`
	AvailableBytes uint64   `json:"availableBytes,omitempty"`
}
type directoryCursor struct {
	UID, Root, Relative, Revision string
	Offset                        int64
	Expires                       time.Time
}
type directoryService struct {
	provider   directoryProvider
	slots      chan struct{}
	mu         sync.Mutex
	cursors    map[string]directoryCursor
	identities map[string]string
}

func newDirectoryService(p directoryProvider) *directoryService {
	if p == nil {
		p = newFnosDirectoryProvider()
	}
	return &directoryService{provider: p, slots: make(chan struct{}, 4), cursors: map[string]directoryCursor{}, identities: map[string]string{}}
}
func directorySafe(p string, absolute bool) bool {
	if len(p) > 4096 || !utf8.ValidString(p) || strings.ContainsAny(p, "\x00\r\n\\") || filepath.IsAbs(p) != absolute {
		return false
	}
	if len(strings.Split(p, "/")) > 128 {
		return false
	}
	for _, v := range strings.Split(p, "/") {
		if v == ".." || v == "." {
			return false
		}
	}
	return true
}
func directoryWithin(root, path string) bool {
	return path == root || strings.HasPrefix(path, root+"/")
}
func directoryHash(v string) string { s := sha256.Sum256([]byte(v)); return hex.EncodeToString(s[:16]) }

// Resource-created shares are a separate platform authorization contract.
// Merge only after live provider success; every candidate still needs user ACL,
// private-tree exclusion and FD-relative filesystem checks. Never trust ACCESSIBLE
// snapshots or qB preferences as a fallback for revoked dynamic grants.
func (s *directoryService) roots(ctx context.Context, uid string) ([]directoryRoot, string, error) {
	counts := map[string]int{"discovered": 0, "unique": 0, "privateExcluded": 0, "aclChecked": 0, "aclDenied": 0, "aclErrors": 0, "filesystemChecked": 0, "packageReadDenied": 0, "mountUnavailable": 0, "mountRejected": 0, "filesystemOther": 0, "available": 0}
	paths, e := s.provider.Roots(ctx)
	if e != nil {
		return nil, "", directoryStage(e, "shared_grants", counts)
	}
	paths = append([]string(nil), paths...)
	for _, path := range strings.Split(os.Getenv("TRIM_DATA_SHARE_PATHS"), ":") {
		if path != "" {
			paths = append(paths, path)
		}
	}
	counts["discovered"] = len(paths)
	if len(paths) > 128 {
		return nil, "", directoryStage(sourceFailure("AUTH_RESPONSE_INVALID"), "shared_grants", counts)
	}
	seen := map[string]bool{}
	var roots []directoryRoot
	var rev []string
	for _, path := range paths {
		if !directorySafe(path, true) || path == "/" {
			return nil, "", errSource
		}
		path = filepath.Clean(path)
		if seen[path] {
			continue
		}
		seen[path] = true
		counts["unique"]++
		// Exclude known private application trees, even if a platform grant is broad.
		if directoryPrivate(path) {
			counts["privateExcluded"]++
			continue
		}
		counts["aclChecked"]++
		a, e := s.provider.ACL(ctx, uid, []string{path})
		if e != nil {
			counts["aclErrors"]++
			return nil, "", directoryStage(e, "user_acl", counts)
		}
		if len(a) != 1 || a[0].Path != path {
			counts["aclErrors"]++
			return nil, "", directoryStage(sourceFailure("AUTH_RESPONSE_INVALID"), "user_acl", counts)
		}
		if !a[0].Readable {
			counts["aclDenied"]++
			counts["ACL_API_DENIED"]++
			continue
		}
		counts["filesystemChecked"]++
		w, e := s.worker(ctx, workerRequest{Root: path})
		if e != nil {
			if fixed := directoryFixedReason(w.Error); fixed != "" {
				counts[fixed]++
			}
			switch w.Error {
			case "package_read_denied":
				counts["packageReadDenied"]++
			case "mount_unavailable":
				counts["mountUnavailable"]++
			case "mount_rejected":
				counts["mountRejected"]++
			default:
				counts["filesystemOther"]++
			}
			continue
		}
		s.mu.Lock()
		old, known := s.identities[path]
		if !known {
			s.identities[path] = w.Identity
		}
		s.mu.Unlock()
		// Replacement/remount requires service restart and fresh platform confirmation.
		if known && old != w.Identity {
			counts["mountRejected"]++
			counts["MOUNT_REJECTED"]++
			continue
		}
		id := directoryHash(path)
		rev = append(rev, path+":"+w.Identity)
		roots = append(roots, directoryRoot{directoryEntry: directoryEntry{Name: filepath.Base(path), CanonicalPath: path, RootID: id, Writable: a[0].Writable && w.Writable}, Source: []string{"sharedGrant"}})
	}
	counts["available"] = len(roots)
	if len(paths) > 0 && len(roots) == 0 {
		reason := "AUTH_ROOTS_INACCESSIBLE"
		for count, code := range map[string]string{"aclDenied": "AUTH_USER_ACL_DENIED", "packageReadDenied": "AUTH_PACKAGE_READ_DENIED", "mountUnavailable": "AUTH_MOUNT_UNAVAILABLE", "mountRejected": "AUTH_MOUNT_REJECTED", "privateExcluded": "AUTH_PRIVATE_ROOTS_EXCLUDED"} {
			if counts[count] == counts["unique"] {
				reason = code
			}
		}
		return nil, "", directoryStage(sourceFailure(reason), "root_filter", counts)
	}
	sort.Strings(rev)
	return roots, directoryHash(strings.Join(rev, "\x00")), nil
}
func directoryPrivate(path string) bool {
	for _, p := range []string{os.Getenv("TRIM_APPDEST"), os.Getenv("TRIM_PKGVAR"), os.Getenv("TRIM_PKGHOME"), filepath.Dir(os.Getenv("BACKEND_PASSWORD_FILE"))} {
		if p != "" && p != "." && p != "/" && directoryWithin(filepath.Clean(p), path) {
			return true
		}
	}
	for _, p := range strings.Split(path, "/") {
		if p == "@appdata" || p == "@appstore" || p == "@apphome" {
			return true
		}
	}
	return false
}
func (s *directoryService) checked(ctx context.Context, uid, path string, roots []directoryRoot, rootID string) (directoryEntry, error) {
	if !directorySafe(path, true) || directoryPrivate(path) {
		return directoryEntry{}, errDirectory
	}
	// Longest root wins for a manual path, keeping nested authorization boundaries.
	candidates := append([]directoryRoot(nil), roots...)
	sort.Slice(candidates, func(i, j int) bool { return len(candidates[i].CanonicalPath) > len(candidates[j].CanonicalPath) })
	for _, root := range candidates {
		if (rootID != "" && root.RootID != rootID) || !directoryWithin(root.CanonicalPath, path) {
			continue
		}
		rel, _ := filepath.Rel(root.CanonicalPath, path)
		if rel == "." {
			rel = ""
		}
		w, e := s.worker(ctx, workerRequest{Root: root.CanonicalPath, Relative: rel})
		if e != nil {
			return directoryEntry{}, e
		}
		a, e := s.provider.ACL(ctx, uid, []string{path})
		if e != nil {
			return directoryEntry{}, directoryStage(e, "user_acl", map[string]int{"aclErrors": 1})
		}
		if len(a) != 1 || a[0].Path != path {
			return directoryEntry{}, directoryStage(sourceFailure("AUTH_RESPONSE_INVALID"), "user_acl", map[string]int{"schemaRejected": 1})
		}
		if !a[0].Readable {
			return directoryEntry{}, directoryStage(errDirectory, "user_acl", map[string]int{"aclDenied": 1, "ACL_API_DENIED": 1})
		}
		return directoryEntry{Name: filepath.Base(path), RelativePath: rel, CanonicalPath: path, RootID: root.RootID, Writable: a[0].Writable && w.Writable}, nil
	}
	return directoryEntry{}, errDirectory
}
func directoryError(w http.ResponseWriter, e error) {
	code := 404
	reason := "DIRECTORY_UNAVAILABLE"
	if errors.Is(e, errSource) {
		code = 503
		reason = "AUTH_SOURCE_UNAVAILABLE"
		var source directorySourceError
		if errors.As(e, &source) {
			reason = string(source)
		}
	}
	if errors.Is(e, context.DeadlineExceeded) {
		code = 504
		reason = "BROWSE_TIMEOUT"
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	payload := map[string]any{"code": reason, "retryable": code >= 500}
	var stage *directoryStageError
	if errors.As(e, &stage) {
		payload["diagnostics"] = stage.diagnostic
	}
	json.NewEncoder(w).Encode(payload)
}
func (s *directoryService) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("Content-Type", "application/json")
	if r.Method != "POST" || r.URL.RawQuery != "" {
		w.WriteHeader(405)
		return
	}
	var q struct {
		RootID   string `json:"rootId"`
		Relative string `json:"relativePath"`
		Manual   string `json:"manualPath"`
		Cursor   string `json:"cursor"`
		Revision string `json:"authorizationRevision"`
		Purpose  string `json:"purpose"`
	}
	if r.Body != nil {
		d := json.NewDecoder(io.LimitReader(r.Body, 16385))
		d.DisallowUnknownFields()
		if e := d.Decode(&q); e != nil && e != io.EOF {
			w.WriteHeader(400)
			return
		}
	}
	if r.URL.Path == prefix+"/gateway/directories/storage" {
		s.storage(w, r)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 3*time.Second)
	defer cancel()
	uid := r.Header.Get("X-Trim-Userid")
	roots, rev, e := s.roots(ctx, uid)
	if e != nil {
		directoryError(w, e)
		return
	}
	action := strings.TrimPrefix(r.URL.Path, prefix+"/gateway/directories/")
	if action == "roots" {
		if roots == nil {
			roots = []directoryRoot{}
		}
		json.NewEncoder(w).Encode(map[string]any{"roots": roots, "authorizationRevision": rev, "reason": func() string {
			if len(roots) == 0 {
				return "NO_APP_GRANTS"
			}
			return "APP_GRANTS_AVAILABLE"
		}()})
		return
	}
	if q.Revision != "" && q.Revision != rev {
		w.WriteHeader(409)
		json.NewEncoder(w).Encode(map[string]string{"code": "AUTHORIZATION_CHANGED"})
		return
	}
	path := q.Manual
	var root directoryRoot
	for _, v := range roots {
		if v.RootID == q.RootID {
			root = v
			break
		}
	}
	if path == "" {
		if root.RootID == "" || !directorySafe(q.Relative, false) {
			directoryError(w, errDirectory)
			return
		}
		path = root.CanonicalPath
		if q.Relative != "" {
			path += "/" + q.Relative
		}
	}
	choice, e := s.checked(ctx, uid, path, roots, q.RootID)
	if e != nil {
		directoryError(w, e)
		return
	}
	if action == "validate" {
		if !choice.Writable {
			w.WriteHeader(422)
			json.NewEncoder(w).Encode(map[string]string{"code": "READ_ONLY"})
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"rootId": choice.RootID, "relativePath": choice.RelativePath, "canonicalPath": choice.CanonicalPath, "writable": true, "authorizationRevision": rev, "checkedAt": time.Now().UTC().Format(time.RFC3339)})
		return
	}
	if action != "browse" {
		w.WriteHeader(404)
		return
	}
	for _, v := range roots {
		if v.RootID == choice.RootID {
			root = v
		}
	}
	offset := int64(0)
	if q.Cursor != "" {
		s.mu.Lock()
		c, ok := s.cursors[q.Cursor]
		delete(s.cursors, q.Cursor)
		s.mu.Unlock()
		if !ok || time.Now().After(c.Expires) || c.UID != uid || c.Root != root.RootID || c.Relative != choice.RelativePath || c.Revision != rev {
			w.WriteHeader(409)
			json.NewEncoder(w).Encode(map[string]string{"code": "CURSOR_EXPIRED"})
			return
		}
		offset = c.Offset
	}
	layer, e := s.worker(ctx, workerRequest{Root: root.CanonicalPath, Relative: choice.RelativePath, List: true, Offset: offset})
	if e != nil {
		directoryError(w, e)
		return
	}
	entries := []directoryEntry{}
	counts := layer.Counts
	if counts == nil {
		counts = map[string]int{}
	}
	for _, item := range layer.Entries {
		entry, e := s.checked(ctx, uid, root.CanonicalPath+"/"+item, roots, root.RootID)
		if errors.Is(e, errSource) || errors.Is(e, context.DeadlineExceeded) {
			var detail *directoryStageError
			if errors.As(e, &detail) {
				for reason, n := range detail.diagnostic.Counts {
					counts[reason] += n
				}
			}
			directoryError(w, directoryStage(e, "child_acl", counts))
			return
		}
		if e == nil {
			entries = append(entries, entry)
		} else {
			counts["childRejected"]++
			var stage *directoryStageError
			if errors.As(e, &stage) {
				for reason, n := range stage.diagnostic.Counts {
					counts[reason] += n
				}
			}
		}
	}
	cursor := ""
	if layer.More {
		s.mu.Lock()
		for k, c := range s.cursors {
			if time.Now().After(c.Expires) {
				delete(s.cursors, k)
			}
		}
		if len(s.cursors) >= 32 {
			s.mu.Unlock()
			w.WriteHeader(429)
			return
		}
		cursor = randomConnectorToken()
		s.cursors[cursor] = directoryCursor{uid, root.RootID, choice.RelativePath, rev, layer.Offset, time.Now().Add(time.Minute)}
		s.mu.Unlock()
	}
	counts["returned"] = len(entries)
	reason := "DIRECTORY_CHILDREN_AVAILABLE"
	if len(entries) == 0 {
		reason = "DIRECTORY_CHILDREN_FILTERED"
		if counts["scanned"] == 0 && !layer.More {
			reason = "DIRECTORY_EMPTY"
		}
	}
	if len(entries) == 0 && layer.More {
		reason = "DIRECTORY_PAGE_FILTERED"
	}
	json.NewEncoder(w).Encode(map[string]any{"entries": entries, "nextCursor": cursor, "canonicalPath": choice.CanonicalPath, "authorizationRevision": rev, "reason": reason, "diagnostics": directoryDiagnostic{"browse_children", counts}})
}

type workerRequest struct {
	Root, Relative string
	List           bool
	Offset         int64
}
type workerResponse struct {
	Identity       string
	VolumeIdentity string
	Writable       bool
	Entries        []string
	Offset         int64
	More           bool
	Error          string
	Counts         map[string]int
	TotalBytes     uint64
	FreeBytes      uint64
	AvailableBytes uint64
}

func (s *directoryService) worker(ctx context.Context, q workerRequest) (workerResponse, error) {
	select {
	case s.slots <- struct{}{}:
	default:
		return workerResponse{}, context.DeadlineExceeded
	}
	defer func() { <-s.slots }()
	exe, e := os.Executable()
	if e != nil {
		return workerResponse{}, errDirectory
	}
	b, _ := json.Marshal(q)
	cmd := exec.CommandContext(ctx, exe, "--directory-worker")
	cmd.Env = []string{"LANG=C.UTF-8", "GORACE=atexit_sleep_ms=0"}
	cmd.Stdin = bytes.NewReader(b)
	cmd.WaitDelay = 100 * time.Millisecond
	var out bytes.Buffer
	cmd.Stdout = &out
	if e = cmd.Run(); e != nil {
		if ctx.Err() != nil {
			return workerResponse{}, ctx.Err()
		}
		return workerResponse{}, errDirectory
	}
	var result workerResponse
	if out.Len() > 256<<10 || json.Unmarshal(out.Bytes(), &result) != nil {
		return workerResponse{}, directoryStage(errDirectory, "worker_response", map[string]int{"invalid": 1})
	}
	if result.Error != "" {
		// Never serialize raw syscall messages or any worker-supplied path.
		reason := "unavailable"
		switch result.Error {
		case "package_read_denied", "mount_unavailable", "mount_rejected", "symlink_rejected":
			reason = result.Error
		}
		counts := map[string]int{reason: 1}
		if fixed := directoryFixedReason(reason); fixed != "" {
			counts[fixed] = 1
		}
		return result, directoryStage(errDirectory, "filesystem_open", counts)
	}
	return result, nil
}
func directoryMount(fd int) (string, error) {
	b, e := os.ReadFile(fmt.Sprintf("/proc/self/fdinfo/%d", fd))
	if e != nil {
		return "", e
	}
	for _, l := range strings.Split(string(b), "\n") {
		if strings.HasPrefix(l, "mnt_id:") {
			return strings.TrimSpace(strings.TrimPrefix(l, "mnt_id:")), nil
		}
	}
	return "", errDirectory
}

// FD-relative O_NOFOLLOW lookup rejects all symlinks, including in-root links.
// Real nested mounts inside a confirmed grant remain subject to child ACL checks;
// mount identity pins the authorized root, not every descendant's filesystem.
func directoryOpen(path string) (int, error) {
	if !directorySafe(path, true) {
		return -1, errDirectory
	}
	// Ancestors are traversal-only handles: O_PATH does not require read
	// permission. The authorized root itself is deliberately O_RDONLY so it
	// must be genuinely enumerable. Every component remains NoFollow-bound.
	fd, e := syscall.Open("/", directoryOPath|syscall.O_DIRECTORY|syscall.O_CLOEXEC, 0)
	if e != nil {
		return -1, e
	}
	parts := strings.Split(strings.TrimPrefix(path, "/"), "/")
	for i, part := range parts {
		if part == "" {
			continue
		}
		flags := directoryOPath | syscall.O_DIRECTORY | syscall.O_NOFOLLOW | syscall.O_CLOEXEC
		if i == len(parts)-1 {
			flags = syscall.O_DIRECTORY | syscall.O_NOFOLLOW | syscall.O_CLOEXEC | syscall.O_RDONLY
		}
		next, e := directoryOpenat(fd, part, flags)
		syscall.Close(fd)
		if e != nil {
			return -1, e
		}
		fd = next
	}
	return fd, nil
}

// Classification probes never follow a link and never authorize a rejected FD.
// Linux O_DIRECTORY|O_NOFOLLOW reports ENOTDIR for both files and links.
var errDirectorySymlink = errors.New("SYMLINK_REJECTED")

func directoryOpenat(fd int, name string, flags int) (int, error) {
	next, e := syscall.Openat(fd, name, flags, 0)
	if errors.Is(e, syscall.ENOTDIR) || errors.Is(e, syscall.ELOOP) {
		probe, pe := syscall.Openat(fd, name, directoryOPath|syscall.O_NOFOLLOW|syscall.O_CLOEXEC, 0)
		if pe == nil {
			var st syscall.Stat_t
			se := syscall.Fstat(probe, &st)
			syscall.Close(probe)
			if se == nil && st.Mode&syscall.S_IFMT == syscall.S_IFLNK {
				return -1, errDirectorySymlink
			}
		}
	}
	return next, e
}
func directoryFixedReason(reason string) string {
	switch reason {
	case "package_read_denied":
		return "PACKAGE_OPEN_EACCES"
	case "symlink_rejected":
		return "SYMLINK_REJECTED"
	case "mount_rejected":
		return "MOUNT_REJECTED"
	default:
		return ""
	}
}
func directoryFilesystemReason(e error) string {
	if errors.Is(e, errDirectorySymlink) || errors.Is(e, syscall.ELOOP) {
		return "symlink_rejected"
	}
	if errors.Is(e, syscall.EACCES) || errors.Is(e, syscall.EPERM) {
		return "package_read_denied"
	}
	if errors.Is(e, syscall.ENOENT) || errors.Is(e, syscall.ENODEV) || errors.Is(e, syscall.ESTALE) {
		return "mount_unavailable"
	}
	if errors.Is(e, syscall.ENOTDIR) {
		return "non_directory"
	}
	return "unavailable"
}
func directoryWork(q workerRequest) workerResponse {
	return directoryWorkRead(q, syscall.ReadDirent)
}

// The seam permits controlled DT_UNKNOWN/errno tests without a production
// environment switch or dependency on a particular network filesystem.
func directoryWorkRead(q workerRequest, readDirent func(int, []byte) (int, error)) (result workerResponse) {
	result.Counts = map[string]int{}
	result.Error = "unavailable"
	if !directorySafe(q.Relative, false) {
		return
	}
	fd, e := directoryOpen(q.Root)
	if e != nil {
		result.Error = directoryFilesystemReason(e)
		return
	}
	defer func() { syscall.Close(fd) }()
	mount, e := directoryMount(fd)
	if e != nil {
		return
	}
	var st syscall.Stat_t
	if syscall.Fstat(fd, &st) != nil {
		return
	}
	result.Identity = fmt.Sprintf("%d:%d:%s", st.Dev, st.Ino, mount)
	result.VolumeIdentity = fmt.Sprintf("%d:%s", st.Dev, mount)
	var fs syscall.Statfs_t
	if syscall.Fstatfs(fd, &fs) != nil {
		result.Error = "unavailable"
		return
	}
	result.TotalBytes = uint64(fs.Blocks) * uint64(fs.Bsize)
	result.FreeBytes = uint64(fs.Bfree) * uint64(fs.Bsize)
	result.AvailableBytes = uint64(fs.Bavail) * uint64(fs.Bsize)
	parts := strings.Split(q.Relative, "/")
	for i, part := range parts {
		if part == "" {
			continue
		}
		flags := directoryOPath | syscall.O_DIRECTORY | syscall.O_NOFOLLOW | syscall.O_CLOEXEC
		if i == len(parts)-1 {
			flags = syscall.O_DIRECTORY | syscall.O_NOFOLLOW | syscall.O_CLOEXEC | syscall.O_RDONLY
		}
		next, e := directoryOpenat(fd, part, flags)
		if e != nil {
			result.Error = directoryFilesystemReason(e)
			return
		}
		syscall.Close(fd)
		fd = next
	}
	// faccessat flags=0 uses real UID; gateway/worker never runs setuid/root.
	result.Writable = syscall.Faccessat(fd, ".", 2|1, 0) == nil
	result.Error = ""
	if !q.List {
		return
	}
	if q.Offset < 0 {
		result.Error = "unavailable"
		return
	}
	if _, e := syscall.Seek(fd, q.Offset, 0); e != nil {
		result.Error = "unavailable"
		return
	}
	buf := make([]byte, 32768)
	scanned := 0
	for scanned < 2000 && len(result.Entries) < 100 {
		n, e := readDirent(fd, buf)
		if e != nil {
			result.Error = directoryFilesystemReason(e)
			return
		}
		if n == 0 {
			return
		}
		for pos := 0; pos < n; {
			d := (*syscall.Dirent)(unsafe.Pointer(&buf[pos]))
			if d.Reclen == 0 {
				result.Error = "unavailable"
				return
			}
			pos += int(d.Reclen)
			result.Offset = d.Off
			scanned++
			raw := (*[256]byte)(unsafe.Pointer(&d.Name[0]))
			end := bytes.IndexByte(raw[:], 0)
			if end < 0 {
				continue
			}
			name := string(raw[:end])
			if name != "." && name != ".." {
				result.Counts["scanned"]++
			}
			if name == "." || name == ".." || !directorySafe(name, false) {
				continue
			}
			child, e := directoryOpenat(fd, name, syscall.O_DIRECTORY|syscall.O_NOFOLLOW|syscall.O_CLOEXEC|syscall.O_RDONLY)
			if e == nil {
				syscall.Close(child)
				rel := name
				if q.Relative != "" {
					rel = q.Relative + "/" + name
				}
				result.Entries = append(result.Entries, rel)
				result.Counts["directories"]++
			} else {
				// DT_UNKNOWN is deliberately not filtered: openat is authoritative.
				// Regular files/symlinks are never opened without O_DIRECTORY/NOFOLLOW.
				reason := directoryFilesystemReason(e)
				result.Counts[reason]++
				if fixed := directoryFixedReason(reason); fixed != "" {
					result.Counts[fixed]++
				}
				result.Counts["child_open_rejected"]++
				if errors.Is(e, syscall.ENOTDIR) || errors.Is(e, syscall.ELOOP) {
					result.Counts["nonDirectoryOrLink"]++
				}
			}
			if scanned >= 2000 || len(result.Entries) >= 100 {
				result.More = true
				return
			}
		}
	}
	result.More = true
	return
}
func init() {
	if len(os.Args) == 2 && os.Args[1] == "--directory-worker" {
		var q workerRequest
		if json.NewDecoder(io.LimitReader(os.Stdin, 16384)).Decode(&q) != nil {
			os.Exit(2)
		}
		json.NewEncoder(os.Stdout).Encode(directoryWork(q))
		os.Exit(0)
	}
}
