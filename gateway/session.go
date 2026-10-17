package main

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"crypto/subtle"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

const sessionCookie = "fnos_qbt_session"
const csrfHeader = "X-Fnos-CSRF"
const sessionTTL = 30 * time.Minute
const maxSessions = 1024

type gatewaySession struct {
	token, origin, uid string
	expires            time.Time
}
type sessionStore struct {
	sync.Mutex
	sessions       map[string]gatewaySession
	now            func() time.Time
	originMismatch uint64
}

func (s *sessionStore) originMismatchCount() uint64 {
	s.Lock()
	defer s.Unlock()
	return s.originMismatch
}

// The fingerprint is intentionally keyed per process: it is only a short equality
// diagnostic, not an authority identifier and cannot be reversed into a hostname.
var originFingerprintKey = func() []byte {
	b := make([]byte, 32)
	if _, e := rand.Read(b); e != nil {
		panic(e)
	}
	return b
}()

func originFingerprint(origin string) string {
	m := hmac.New(sha256.New, originFingerprintKey)
	_, _ = m.Write([]byte(origin))
	return hex.EncodeToString(m.Sum(nil))[:12]
}
func originPortClass(origin string) string {
	u, e := url.Parse(origin)
	if e != nil {
		return "invalid"
	}
	switch {
	case u.Scheme == "http" && u.Port() == "":
		return "http-default"
	case u.Scheme == "https" && u.Port() == "":
		return "https-default"
	case u.Scheme == "http":
		return "http-nondefault"
	case u.Scheme == "https":
		return "https-nondefault"
	default:
		return "invalid"
	}
}

func newSessionStore() *sessionStore {
	return &sessionStore{sessions: make(map[string]gatewaySession), now: time.Now}
}
func randomSecret() (string, error) {
	b := make([]byte, 32)
	_, err := rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b), err
}
func sourceOrigin(value string, referer bool) string {
	u, err := url.Parse(value)
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") || u.Host == "" || u.User != nil || u.Fragment != "" || u.Opaque != "" {
		return ""
	}
	if !referer && (u.Path != "" || u.RawQuery != "" || u.ForceQuery) {
		return ""
	}
	return u.Scheme + "://" + strings.ToLower(u.Host)
}

// Host may be rewritten by fnOS. Browser source is established by a non-simple,
// same-origin bootstrap request, NOT by forwarding headers or an origin allowlist.
// SOP + no CORS prevent another origin from obtaining/using the session token.
func browserSourceReason(r *http.Request) (string, string) {
	if site := r.Header.Get("Sec-Fetch-Site"); site != "" && site != "same-origin" {
		return "", "fetch_site_not_same_origin"
	}
	var origin string
	for _, name := range []string{"Origin", "Referer"} {
		if len(r.Header.Values(name)) > 1 {
			return "", "origin_referer_mismatch"
		}
		if v := r.Header.Get(name); v != "" {
			o := sourceOrigin(v, name == "Referer")
			if o == "" || (origin != "" && o != origin) {
				return "", "origin_referer_mismatch"
			}
			origin = o
		}
	}
	if origin == "" {
		return "", "origin_or_referer_missing"
	}
	return origin, ""
}
func browserSource(r *http.Request) string { o, _ := browserSourceReason(r); return o }
func gatewayHandler(proxy http.Handler) http.Handler {
	return gatewayHandlerStore(proxy, newSessionStore())
}

// Kept only for source compatibility with older local harnesses; no allowlist is used.
func gatewayHandlerOrigins(proxy http.Handler, _ []string) http.Handler { return gatewayHandler(proxy) }
func gatewayHandlerStore(proxy http.Handler, s *sessionStore) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != prefix && !strings.HasPrefix(r.URL.Path, prefix+"/") {
			http.NotFound(w, r)
			return
		}
		// Reject traversal before the static/navigation exception; qB may normalize it.
		if strings.Contains(r.URL.Path, "\\\\") || strings.Contains(r.URL.Path, "//") {
			http.NotFound(w, r)
			return
		}
		for _, segment := range strings.Split(r.URL.Path, "/") {
			if segment == "." || segment == ".." {
				http.NotFound(w, r)
				return
			}
		}
		w.Header().Set("Referrer-Policy", "same-origin")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		safe := r.Method == "GET" || r.Method == "HEAD"
		navigation := safe && (r.URL.Path == prefix || r.URL.Path == prefix+"/" || strings.HasPrefix(r.URL.Path, prefix+"/assets/"))
		if navigation {
			// Navigation is not authorization and cannot perform backend API actions.
			r.Header.Del("Origin")
			r.Header.Del("Referer")
			if r.URL.Path == prefix {
				http.Redirect(w, r, prefix+"/", 308)
				return
			}
			proxy.ServeHTTP(w, r)
			return
		}
		w.Header().Set("Cache-Control", "no-store")
		reject := func(code int, reason string) {
			w.Header().Set("X-Fnos-Gateway-Reason", reason)
			stage := "api"
			if r.URL.Path == prefix+"/gateway/session" {
				stage = "bootstrap"
			}
			log.Printf("gateway reject stage=%s reason=%s", stage, reason)
			w.Header().Set("X-Fnos-Gateway-Error", "session")
			http.Error(w, "gateway session required", code)
		}
		// Every protected call must still pass fnOS authentication. Header values are
		// authoritative ONLY because the listener is private Unix, never public TCP.
		if r.Header.Get("X-Trim-Isadmin") != "true" || r.Header.Get("X-Trim-Userid") == "" {
			reject(403, "missing_trim_identity")
			return
		}
		origin, sourceReason := browserSourceReason(r)
		if origin == "" || r.Method == "OPTIONS" {
			if sourceReason == "" {
				sourceReason = "origin_or_referer_missing"
			}
			reject(403, sourceReason)
			return
		}
		bootstrap := r.URL.Path == prefix+"/gateway/session"
		if bootstrap && (r.Method != "POST" || r.Header.Get("X-Fnos-Bootstrap") != "1" || r.URL.RawQuery != "") {
			reject(403, "csrf_missing_or_invalid")
			return
		}
		if strings.Contains(strings.ToLower(r.URL.RawQuery), "token") {
			reject(403, "csrf_missing_or_invalid")
			return
		}
		s.Lock()
		defer s.Unlock()
		now := s.now()
		expiredID := ""
		if c, e := r.Cookie(sessionCookie); e == nil {
			if old, ok := s.sessions[c.Value]; ok && !now.Before(old.expires) {
				expiredID = c.Value
			}
		}
		for id, session := range s.sessions {
			if !now.Before(session.expires) {
				delete(s.sessions, id)
			}
		}
		id := ""
		if c, err := r.Cookie(sessionCookie); err == nil {
			id = c.Value
		}
		session, valid := s.sessions[id]
		valid = valid && session.origin == origin && session.uid == r.Header.Get("X-Trim-Userid")
		cookie := func(value string, age int) {
			secure := strings.HasPrefix(origin, "https://")
			sameSite := http.SameSiteStrictMode
			// fnOS App WebViews may embed the gateway under a different site
			// authority. Allow cookie transport only on HTTPS; origin, Fetch
			// Metadata, UID and CSRF token checks remain mandatory below.
			if secure {
				sameSite = http.SameSiteNoneMode
			}
			http.SetCookie(w, &http.Cookie{Name: sessionCookie, Value: value, Path: prefix + "/", HttpOnly: true, Secure: secure, SameSite: sameSite, MaxAge: age})
		}
		if bootstrap {
			if !valid {
				if len(s.sessions) >= maxSessions {
					http.Error(w, "gateway session capacity reached", 503)
					return
				}
				var err error
				id, err = randomSecret()
				if err != nil {
					http.Error(w, "session unavailable", 503)
					return
				}
				token, err := randomSecret()
				if err != nil {
					http.Error(w, "session unavailable", 503)
					return
				}
				session = gatewaySession{token: token, origin: origin, uid: r.Header.Get("X-Trim-Userid"), expires: now.Add(sessionTTL)}
				s.sessions[id] = session
			}
			cookie(id, int(session.expires.Sub(now).Seconds()))
			w.Header().Set("Content-Type", "application/json")
			_ = json.NewEncoder(w).Encode(map[string]any{"token": session.token, "expiresIn": int(session.expires.Sub(now).Seconds())})
			return
		}
		reason := ""
		if id == "" {
			reason = "session_cookie_missing"
		} else if expiredID == id {
			reason = "session_expired"
		} else if _, ok := s.sessions[id]; !ok {
			reason = "session_expired"
		} else if session.origin != origin {
			reason = "session_origin_mismatch"
		} else if session.uid != r.Header.Get("X-Trim-Userid") {
			reason = "session_uid_mismatch"
		} else if len(r.Header.Values(csrfHeader)) != 1 || subtle.ConstantTimeCompare([]byte(r.Header.Get(csrfHeader)), []byte(session.token)) != 1 {
			reason = "csrf_missing_or_invalid"
		}
		if reason != "" {
			if reason == "session_origin_mismatch" {
				s.originMismatch++
				w.Header().Set("X-Fnos-Gateway-Reason", reason)
				w.Header().Set("Content-Type", "application/json")
				w.WriteHeader(http.StatusForbidden)
				_ = json.NewEncoder(w).Encode(map[string]any{"error": "session_origin_mismatch", "reason": "session_origin_mismatch", "session_origin_fingerprint": originFingerprint(session.origin), "request_origin_fingerprint": originFingerprint(origin), "session_origin_port_class": originPortClass(session.origin), "request_origin_port_class": originPortClass(origin), "bootstrap_origin_changed": true})
				return
			}
			reject(403, reason)
			return
		}
		if r.URL.Path == prefix+"/gateway/logout" || r.URL.Path == prefix+"/api/v2/auth/logout" {
			if r.Method != "POST" {
				reject(403, "csrf_missing_or_invalid")
				return
			}
			delete(s.sessions, id)
			cookie("", -1)
			w.WriteHeader(204)
			return
		}
		if !strings.HasPrefix(r.URL.Path, prefix+"/api/v2/") {
			http.NotFound(w, r)
			return
		}
		// Never expose application credentials to the backend or response diagnostics.
		r.Header.Del(csrfHeader)
		r.Header.Del("X-Fnos-Bootstrap")
		var cookies []string
		for _, c := range r.Cookies() {
			if c.Name != sessionCookie {
				cookies = append(cookies, c.String())
			}
		}
		r.Header.Del("Cookie")
		if len(cookies) > 0 {
			r.Header.Set("Cookie", strings.Join(cookies, "; "))
		}
		// Unlock across backend I/O; expiry/logout invalidates subsequent requests.
		s.Unlock()
		proxy.ServeHTTP(w, r)
		s.Lock()
	})
}
