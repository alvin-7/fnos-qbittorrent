package main

// Independent machine-client ingress. Never share its sessions with fnOS or qB.
import (
	"bytes"
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"
)

type connectorInput struct {
	Enabled      bool     `json:"enabled"`
	BindIP       string   `json:"bindIP"`
	Port         int      `json:"port"`
	Username     string   `json:"username"`
	Password     string   `json:"password,omitempty"`
	AllowedCIDRs []string `json:"-"` // legacy source compatibility only; ignored
	TrustedHTTP  bool     `json:"-"` // HTTP risk is explicitly documented, not a checkbox
}
type connectorConfig struct {
	connectorInput
	Salt   string `json:"salt"`
	Hash   string `json:"hash"`
	Secret string `json:"secret,omitempty"`
	Schema int    `json:"schema"`
}
type connectorStatus struct {
	connectorInput
	PasswordSet           bool   `json:"passwordSet"`
	Listening             bool   `json:"listening"`
	ContainerReachability string `json:"containerReachability"`
}
type connectorSession struct {
	peer    string
	expires time.Time
}
type connector struct {
	mu         sync.Mutex
	requestMu  sync.Mutex // bounded machine-client work; never blocks management
	generation uint64
	dir        string
	cfg        connectorConfig
	proxy      http.Handler
	listener   net.Listener
	server     *http.Server
	sessions   map[string]connectorSession
	failures   int
	cooldown   time.Time
	window     time.Time
	requests   int
}

func newConnector(dir string, p http.Handler) *connector {
	return &connector{dir: dir, proxy: p, sessions: map[string]connectorSession{}}
}
func defaultConnectorInput() connectorInput {
	return connectorInput{Enabled: false, BindIP: "0.0.0.0", Port: 18081, Username: "moviepilot", AllowedCIDRs: []string{}, TrustedHTTP: true}
}
func (c *connector) keyFile() string { return filepath.Join(c.dir, "connector.key") }
func (c *connector) ensureKey() ([]byte, error) {
	if s, e := os.Lstat(c.keyFile()); e == nil {
		if !s.Mode().IsRegular() || s.Mode().Perm() != 0600 {
			return nil, errors.New("private_storage_permissions")
		}
		b, e := os.ReadFile(c.keyFile())
		if e != nil || len(b) != 32 {
			return nil, errors.New("private_storage_invalid")
		}
		return b, nil
	}
	b := make([]byte, 32)
	if _, e := rand.Read(b); e != nil {
		return nil, e
	}
	f, e := os.OpenFile(c.keyFile(), os.O_WRONLY|os.O_CREATE|os.O_EXCL, 0600)
	if e != nil {
		return nil, e
	}
	if _, e = f.Write(b); e == nil {
		e = f.Sync()
	}
	f.Close()
	if e != nil {
		os.Remove(c.keyFile())
		return nil, e
	}
	return b, nil
}
func (c *connector) encryptSecret(password string) (string, error) {
	key, e := c.ensureKey()
	if e != nil {
		return "", e
	}
	block, e := aes.NewCipher(key)
	if e != nil {
		return "", e
	}
	g, e := cipher.NewGCM(block)
	if e != nil {
		return "", e
	}
	nonce := make([]byte, g.NonceSize())
	if _, e = rand.Read(nonce); e != nil {
		return "", e
	}
	return base64.RawStdEncoding.EncodeToString(g.Seal(nonce, nonce, []byte(password), nil)), nil
}
func (c *connector) revealSecret() (string, error) {
	c.mu.Lock()
	secret := c.cfg.Secret
	key, e := c.revealKeyLocked()
	c.mu.Unlock()
	if e != nil {
		return "", e
	}
	return decryptConnectorSecret(secret, key)
}
func (c *connector) revealKeyLocked() ([]byte, error) {
	if s, e := os.Lstat(c.keyFile()); e != nil || !s.Mode().IsRegular() || s.Mode().Perm() != 0600 {
		return nil, errors.New("private_storage_permissions")
	}
	return os.ReadFile(c.keyFile())
}
func decryptConnectorSecret(secret string, key []byte) (string, error) {
	raw, e := base64.RawStdEncoding.DecodeString(secret)
	if e != nil {
		return "", e
	}
	block, e := aes.NewCipher(key)
	if e != nil {
		return "", e
	}
	g, e := cipher.NewGCM(block)
	if e != nil || len(raw) < g.NonceSize() {
		return "", errors.New("private_storage_invalid")
	}
	plain, e := g.Open(nil, raw[:g.NonceSize()], raw[g.NonceSize():], nil)
	return string(plain), e
}
func (c *connector) file() string { return filepath.Join(c.dir, "connector.json") }
func (c *connector) status() connectorStatus {
	c.mu.Lock()
	defer c.mu.Unlock()
	v := c.cfg.connectorInput
	v.Password = ""
	return connectorStatus{v, c.cfg.Hash != "", c.listener != nil, "not_verified_from_container"}
}

// PBKDF2-HMAC-SHA256, 600000 iterations, 256-bit salt/key. Versioned storage.
func connectorHash(password, salt string) string {
	mac := hmac.New(sha256.New, []byte(password))
	mac.Write([]byte(salt))
	mac.Write([]byte{0, 0, 0, 1})
	u := mac.Sum(nil)
	out := append([]byte{}, u...)
	for i := 1; i < 600000; i++ {
		mac.Reset()
		mac.Write(u)
		u = mac.Sum(u[:0])
		for j := range out {
			out[j] ^= u[j]
		}
	}
	return hex.EncodeToString(out)
}
func randomConnectorToken() string {
	b := make([]byte, 32)
	if _, e := rand.Read(b); e != nil {
		panic("secure random unavailable")
	}
	return hex.EncodeToString(b)
}
func localConnectorIP(ip string) bool {
	n := net.ParseIP(ip)
	if n == nil || n.IsUnspecified() || n.IsMulticast() {
		return false
	}
	as, e := net.InterfaceAddrs()
	if e != nil {
		return false
	}
	for _, a := range as {
		v, _, _ := net.ParseCIDR(a.String())
		if n.Equal(v) {
			return true
		}
	}
	return false
}
func validConnectorConfig(v connectorInput) bool {
	if (v.BindIP != "0.0.0.0" && !localConnectorIP(v.BindIP)) || v.Port < 1024 || v.Port > 65535 || v.Port == 18080 || v.Port == 49160 || len(v.Username) < 1 || len(v.Username) > 128 || strings.ContainsAny(v.Username, "\r\n\x00") || strings.ContainsAny(v.Password, "\r\n\x00") {
		return false
	}
	return true
}
func (c *connector) closeLocked() {
	c.sessions = map[string]connectorSession{}
	if c.server != nil {
		c.server.Close()
	}
	c.server = nil
	c.listener = nil
}
func (c *connector) close() { c.mu.Lock(); defer c.mu.Unlock(); c.closeLocked() }
func (c *connector) configure(v connectorInput) error {
	// Slow PBKDF2 does not exclude status, revocation, or another disable.
	var salt, hash string
	c.mu.Lock()
	generation := c.generation
	c.mu.Unlock()
	if v.Password != "" {
		if len([]byte(v.Password)) > 1024 || strings.ContainsAny(v.Password, "\r\n\x00") {
			return errors.New("password_requires_1_to_1024_utf8_bytes")
		}
		salt = randomConnectorToken()
		hash = connectorHash(v.Password, salt)
	}
	c.mu.Lock()
	defer c.mu.Unlock()
	if generation != c.generation {
		return errors.New("connector_save_failed")
	}
	lan := v.BindIP == "" || v.BindIP == "0.0.0.0"
	schema := 2
	v.AllowedCIDRs = nil
	v.TrustedHTTP = true
	if lan {
		v.BindIP = "0.0.0.0"
	}
	next := connectorConfig{connectorInput: v, Schema: schema, Salt: c.cfg.Salt, Hash: c.cfg.Hash, Secret: c.cfg.Secret}
	next.Password = ""
	if v.Password != "" {
		if len([]byte(v.Password)) > 1024 || len([]byte(v.Password)) < 1 || strings.ContainsAny(v.Password, "\r\n\x00") {
			return errors.New("password_requires_1_to_1024_utf8_bytes")
		}
		next.Salt = salt
		next.Hash = hash
		secret, e := c.encryptSecret(v.Password)
		if e != nil {
			return errors.New("private_storage_permissions")
		}
		next.Secret = secret
	}
	if v.Enabled && (!validConnectorConfig(v) || next.Hash == "") {
		return errors.New("invalid_connector_scope_or_credentials")
	}
	var ln net.Listener
	var e error
	same := c.listener != nil && v.Enabled && v.BindIP == c.cfg.BindIP && v.Port == c.cfg.Port
	if v.Enabled && !same {
		ln, e = net.Listen("tcp4", net.JoinHostPort(v.BindIP, strconv.Itoa(v.Port)))
		if e != nil {
			return errors.New("connector_bind_failed")
		}
		actual, ok := ln.Addr().(*net.TCPAddr)
		if !ok || !actual.IP.Equal(net.ParseIP(v.BindIP)) || actual.Port != v.Port {
			ln.Close()
			return errors.New("connector_bind_address_mismatch")
		}
	}
	if e = os.MkdirAll(c.dir, 0700); e != nil {
		if ln != nil {
			ln.Close()
		}
		return errors.New("private_storage_unavailable")
	}
	if e = os.Chmod(c.dir, 0700); e != nil {
		if ln != nil {
			ln.Close()
		}
		return errors.New("private_storage_unavailable")
	}
	info, e := os.Lstat(c.dir)
	if e != nil || !info.IsDir() || info.Mode().Perm() != 0700 {
		if ln != nil {
			ln.Close()
		}
		return errors.New("private_storage_permissions")
	}
	data, _ := json.Marshal(next)
	f, e := os.CreateTemp(c.dir, ".connector-")
	if e == nil {
		e = f.Chmod(0600)
		if e == nil {
			_, e = f.Write(data)
		}
		if e == nil {
			e = f.Sync()
		}
		f.Close()
		if e == nil {
			e = os.Rename(f.Name(), c.file())
		}
		os.Remove(f.Name())
	}
	if e != nil {
		if ln != nil {
			ln.Close()
		}
		return errors.New("connector_save_failed")
	}
	d, e := os.Open(c.dir)
	if e == nil {
		d.Sync()
		d.Close()
	}
	c.sessions = map[string]connectorSession{}
	if !same {
		c.closeLocked()
	}
	c.cfg = next
	c.generation++
	if ln != nil {
		c.listener = ln
		c.server = &http.Server{Handler: c, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 60 * time.Second, WriteTimeout: 60 * time.Second, IdleTimeout: 30 * time.Second, MaxHeaderBytes: 16 << 10}
		go func(s *http.Server, l net.Listener) {
			if err := s.Serve(l); err != nil && err != http.ErrServerClosed {
				println("connector listener failed")
			}
		}(c.server, ln)
	}
	return nil
}
func (c *connector) load() error {
	s, e := os.Lstat(c.file())
	if os.IsNotExist(e) {
		return c.configure(defaultConnectorInput())
	}
	if e != nil || !s.Mode().IsRegular() || s.Mode().Perm() != 0600 {
		return errors.New("connector_storage_permissions")
	}
	d, e := os.Lstat(c.dir)
	if e != nil || !d.IsDir() || d.Mode().Perm() != 0700 {
		return errors.New("connector_storage_permissions")
	}
	b, e := os.ReadFile(c.file())
	if e != nil {
		return errors.New("connector_load_failed")
	}
	var v connectorConfig
	if json.Unmarshal(b, &v) != nil || (v.Schema != 1 && v.Schema != 2) || (v.Enabled && (len(v.Hash) != 64 || len(v.Salt) != 64)) {
		return errors.New("connector_storage_invalid")
	}
	c.cfg = v
	return c.configure(v.connectorInput)
}
func (c *connector) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if !c.requestMu.TryLock() {
		http.Error(w, "connector_busy", 429)
		return
	}
	defer c.requestMu.Unlock() // no unbounded request queue
	c.mu.Lock()
	locked := true
	defer func() {
		if locked {
			c.mu.Unlock()
		}
	}()
	cfg, generation := c.cfg, c.generation
	w.Header().Set("Cache-Control", "no-store")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	deny := func(code int) { http.Error(w, "connector_request_rejected", code) }
	if !c.cfg.Enabled || c.listener == nil {
		deny(503)
		return
	}
	now := time.Now()
	if now.Sub(c.window) >= time.Second {
		c.window = now
		c.requests = 0
	}
	c.requests++
	if c.requests > 60 {
		deny(429)
		return
	}
	peer, _, e := net.SplitHostPort(r.RemoteAddr)
	if e != nil {
		deny(403)
		return
	}
	host, port, e := net.SplitHostPort(r.Host)
	if e != nil || port != strconv.Itoa(c.cfg.Port) || (host != "host.docker.internal" && host != c.cfg.BindIP && !(c.cfg.Schema == 2 && localConnectorIP(host))) {
		deny(403)
		return
	}
	// Browser-less clients may omit source headers; browsers may not cross origins.
	for _, h := range []string{"Origin", "Referer"} {
		if v := r.Header.Get(h); v != "" {
			u, e := url.Parse(v)
			if e != nil || u.Scheme != "http" || u.Host != r.Host || u.User != nil {
				deny(403)
				return
			}
		}
	}
	if site := r.Header.Get("Sec-Fetch-Site"); site != "" && site != "same-origin" {
		deny(403)
		return
	}
	if r.Method == "OPTIONS" || r.URL.RawPath != "" || strings.ContainsAny(r.URL.Path, "\\%") || strings.Contains(r.URL.Path, "//") {
		deny(403)
		return
	}
	route := strings.TrimPrefix(r.URL.Path, "/api/v2/")
	if route == r.URL.Path || strings.EqualFold(route, "app/getDirectoryContent") {
		deny(404)
		return
	}
	if route == "auth/login" {
		if r.Method != "POST" || r.URL.RawQuery != "" {
			deny(405)
			return
		}
		if now.Before(c.cooldown) {
			deny(429)
			return
		}
		c.mu.Unlock()
		locked = false
		r.Body = http.MaxBytesReader(w, r.Body, 4096)
		if r.ParseForm() != nil || len(r.PostForm["username"]) != 1 || len(r.PostForm["password"]) != 1 {
			deny(400)
			return
		}
		match := connectorHash(r.PostForm.Get("password"), cfg.Salt)
		c.mu.Lock()
		locked = true
		if generation != c.generation || !c.cfg.Enabled || c.listener == nil {
			deny(503)
			return
		}
		if subtle.ConstantTimeCompare([]byte(match), []byte(cfg.Hash)) != 1 || r.PostForm.Get("username") != cfg.Username {
			c.failures++
			if c.failures >= 5 {
				c.cooldown = now.Add(time.Minute)
			}
			deny(403)
			return
		}
		for k, v := range c.sessions {
			if now.After(v.expires) {
				delete(c.sessions, k)
			}
		}
		if len(c.sessions) >= 128 {
			deny(429)
			return
		}
		token := randomConnectorToken()
		c.sessions[token] = connectorSession{peer, now.Add(12 * time.Hour)}
		c.failures = 0
		http.SetCookie(w, &http.Cookie{Name: "SID", Value: token, Path: "/", HttpOnly: true, SameSite: http.SameSiteStrictMode})
		io.WriteString(w, "Ok.")
		return
	}
	cookie, e := r.Cookie("SID")
	if e != nil {
		deny(403)
		return
	}
	session, ok := c.sessions[cookie.Value]
	if !ok || now.After(session.expires) || session.peer != peer {
		deny(403)
		return
	}
	if route == "auth/logout" {
		if r.Method != "POST" {
			deny(405)
			return
		}
		delete(c.sessions, cookie.Value)
		http.SetCookie(w, &http.Cookie{Name: "SID", Value: "", Path: "/", MaxAge: -1, HttpOnly: true, SameSite: http.SameSiteStrictMode})
		w.WriteHeader(200)
		return
	}
	// API syntax boundary, not a business-endpoint allowlist. Parameters and bytes
	// belong to qB; in particular do not normalize POST reads or multipart bodies.
	parts := strings.Split(route, "/")
	if len(parts) != 2 || parts[0] == "connector" || parts[0] == "diagnostics" || parts[0] == "auth" {
		deny(404)
		return
	}
	for _, part := range parts {
		if part == "" {
			deny(404)
			return
		}
		for _, ch := range part {
			if !(ch >= 'a' && ch <= 'z' || ch >= 'A' && ch <= 'Z' || ch >= '0' && ch <= '9' || ch == '_') {
				deny(404)
				return
			}
		}
	}
	c.mu.Unlock()
	locked = false
	r.Body = http.MaxBytesReader(w, r.Body, 16<<20)
	body, e := io.ReadAll(r.Body)
	if e != nil {
		deny(413)
		return
	}
	c.mu.Lock()
	_, active := c.sessions[cookie.Value]
	valid := active && generation == c.generation && c.cfg.Enabled && c.listener != nil
	c.mu.Unlock()
	if !valid {
		deny(503)
		return
	}
	if c.proxy == nil {
		deny(503)
		return
	}
	ctx, cancel := context.WithTimeout(r.Context(), 45*time.Second)
	defer cancel()
	request := r.Clone(ctx)
	request.URL.Path = prefix + r.URL.Path
	request.Body = io.NopCloser(bytes.NewReader(body))
	request.ContentLength = int64(len(body))
	request.GetBody = nil
	request.Header = make(http.Header)
	for _, h := range []string{"Content-Type", "Accept", "Accept-Encoding", "Range", "If-None-Match", "If-Modified-Since"} {
		if v := r.Header.Values(h); len(v) > 0 {
			request.Header[h] = append([]string(nil), v...)
		}
	}
	request.Host = "127.0.0.1:18080"
	// Context marker is internal-only, never derived from an HTTP header.
	request = request.WithContext(context.WithValue(ctx, connectorProxyKey{}, true))
	result := &connectorResponse{header: make(http.Header)}
	c.proxy.ServeHTTP(result, request) // exactly once: never replay ambiguous writes
	if ctx.Err() != nil {
		http.Error(w, "connector_backend_timeout", 504)
		return
	}
	if result.overflow {
		http.Error(w, "connector_response_too_large", 502)
		return
	}
	for k, v := range result.header {
		lower := strings.ToLower(k)
		if lower == "set-cookie" || lower == "connection" || lower == "transfer-encoding" || lower == "location" || strings.HasPrefix(lower, "access-control-") {
			continue
		}
		w.Header()[k] = v
	}
	code := result.code
	if code == 0 {
		code = 200
	}
	w.WriteHeader(code)
	w.Write(result.body.Bytes())
}

type connectorProxyKey struct{}
type connectorResponse struct {
	header   http.Header
	body     bytes.Buffer
	code     int
	overflow bool
}

func (w *connectorResponse) Header() http.Header { return w.header }
func (w *connectorResponse) WriteHeader(code int) {
	if w.code == 0 {
		w.code = code
	}
}
func (w *connectorResponse) Write(p []byte) (int, error) {
	if w.code == 0 {
		w.code = 200
	}
	if w.body.Len()+len(p) > 32<<20 {
		w.overflow = true
		return 0, errors.New("connector_response_too_large")
	}
	return w.body.Write(p)
}

type connectorRevealResponse struct {
	Password string `json:"password"`
}

func (c *connector) management(w http.ResponseWriter, r *http.Request) {
	route := strings.TrimPrefix(r.URL.Path, prefix+"/api/v2/connector/")
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	switch {
	case route == "status" && r.Method == "GET":
		json.NewEncoder(w).Encode(c.status())
	case route == "password/reveal" && r.Method == "POST":
		r.Body = http.MaxBytesReader(w, r.Body, 1024)
		if r.ParseForm() != nil || r.PostForm.Get("confirm") != "show-saved-password" {
			http.Error(w, "confirmation_required", 403)
			return
		}
		secret, e := c.revealSecret()
		if e != nil {
			http.Error(w, "saved_password_unavailable", 409)
			return
		}
		json.NewEncoder(w).Encode(connectorRevealResponse{secret})
	case route == "configure" && r.Method == "POST":
		r.Body = http.MaxBytesReader(w, r.Body, 16384)
		if r.ParseForm() != nil {
			http.Error(w, "invalid_configuration", 400)
			return
		}
		var v connectorInput
		if len(r.PostForm["json"]) != 1 || json.Unmarshal([]byte(r.PostForm.Get("json")), &v) != nil {
			http.Error(w, "invalid_configuration", 400)
			return
		}
		if e := c.configure(v); e != nil {
			reason := "connector_save_failed"
			switch e.Error() {
			case "connector_bind_failed", "connector_bind_address_mismatch":
				reason = "connector_bind_failed"
			case "invalid_connector_scope_or_credentials", "password_requires_1_to_1024_utf8_bytes":
				reason = "invalid_connector_scope_or_credentials"
			case "private_storage_unavailable", "private_storage_permissions":
				reason = "private_storage_permissions"
			}
			w.WriteHeader(http.StatusConflict)
			json.NewEncoder(w).Encode(map[string]string{"reason": reason})
			return
		}
		json.NewEncoder(w).Encode(c.status())
	case route == "test" && r.Method == "POST":
		// Backend-only read probe. This is never reported as container reachability.
		req := httptest.NewRequest("GET", "http://127.0.0.1:18080"+prefix+"/api/v2/app/version", nil)
		res := httptest.NewRecorder()
		if c.proxy != nil {
			c.proxy.ServeHTTP(res, req)
		}
		json.NewEncoder(w).Encode(map[string]any{"backendReady": res.Code == 200 && strings.TrimSpace(res.Body.String()) == "v5.2.4", "containerReachability": "not_verified_from_container", "businessWrites": 0})
	default:
		http.NotFound(w, r)
	}
}
