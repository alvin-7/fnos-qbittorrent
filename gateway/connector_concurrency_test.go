package main

import (
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

type connectorBlockedBody struct {
	started chan struct{}
	release chan struct{}
	once    sync.Once
}

func (b *connectorBlockedBody) Read(p []byte) (int, error) {
	b.once.Do(func() { close(b.started) })
	<-b.release
	return 0, io.EOF
}
func (b *connectorBlockedBody) Close() error { return nil }
func concurrencyConnector(t *testing.T, proxy http.Handler) *connector {
	t.Helper()
	c := newConnector(t.TempDir(), proxy)
	c.cfg = connectorConfig{connectorInput: connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18984, Username: "fixture"}, Schema: 2, Salt: "fixture", Hash: strings.Repeat("0", 64)}
	c.listener = &fixtureListener{}
	c.sessions["fixture-session"] = connectorSession{"127.0.0.1", time.Now().Add(time.Hour)}
	return c
}

// Non-network listener: requests are dispatched directly to exercise lock scope.
type fixtureListener struct{}

func (*fixtureListener) Accept() (net.Conn, error) { panic("unused") }
func (*fixtureListener) Close() error              { return nil }
func (*fixtureListener) Addr() net.Addr {
	return &net.TCPAddr{IP: net.ParseIP("127.0.0.1"), Port: 18984}
}

func TestConnectorSlowBodyDoesNotBlockStatusOrDisable(t *testing.T) {
	c := concurrencyConnector(t, nil)
	body := &connectorBlockedBody{started: make(chan struct{}), release: make(chan struct{})}
	r := httptest.NewRequest("POST", "http://127.0.0.1:18984/api/v2/auth/login", body)
	r.RemoteAddr = "127.0.0.1:1234"
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	done := make(chan struct{})
	go func() { c.ServeHTTP(httptest.NewRecorder(), r); close(done) }()
	<-body.started
	responsive := make(chan struct{})
	go func() { c.status(); _ = c.configure(defaultConnectorInput()); close(responsive) }()
	select {
	case <-responsive:
	case <-time.After(250 * time.Millisecond):
		close(body.release)
		<-done
		<-responsive
		t.Fatal("slow request body blocked status/disable")
	}
	close(body.release)
	<-done
}
func TestConnectorBackendDoesNotBlockStatusOrDisable(t *testing.T) {
	started, release := make(chan struct{}), make(chan struct{})
	c := concurrencyConnector(t, http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { close(started); <-release; w.WriteHeader(200) }))
	r := httptest.NewRequest("GET", "http://127.0.0.1:18984/api/v2/app/version", nil)
	r.RemoteAddr = "127.0.0.1:1234"
	r.AddCookie(&http.Cookie{Name: "SID", Value: "fixture-session"})
	done := make(chan struct{})
	go func() { c.ServeHTTP(httptest.NewRecorder(), r); close(done) }()
	<-started
	responsive := make(chan struct{})
	go func() { c.status(); _ = c.configure(defaultConnectorInput()); close(responsive) }()
	select {
	case <-responsive:
	case <-time.After(250 * time.Millisecond):
		close(release)
		<-done
		<-responsive
		t.Fatal("backend blocked status/disable")
	}
	close(release)
	<-done
}
func TestConnectorSlowHashDoesNotBlockStatus(t *testing.T) {
	c := concurrencyConnector(t, nil)
	r := httptest.NewRequest("POST", "http://127.0.0.1:18984/api/v2/auth/login", strings.NewReader("username=fixture&password=synthetic"))
	r.RemoteAddr = "127.0.0.1:1234"
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	done := make(chan struct{})
	go func() { c.ServeHTTP(httptest.NewRecorder(), r); close(done) }()
	deadline := time.Now().Add(time.Second)
	for c.requestMu.TryLock() {
		c.requestMu.Unlock()
		if time.Now().After(deadline) {
			t.Fatal("request did not start")
		}
		time.Sleep(time.Millisecond)
	}
	time.Sleep(10 * time.Millisecond)
	ready := make(chan struct{})
	go func() { c.status(); close(ready) }()
	select {
	case <-ready:
	case <-time.After(100 * time.Millisecond):
		<-done
		t.Fatal("PBKDF2 blocked status")
	}
	<-done
}
func TestConnectorRevealConcurrentConfigure(t *testing.T) {
	c := newConnector(t.TempDir(), nil)
	v := defaultConnectorInput()
	v.Password = "synthetic-concurrency-fixture"
	if e := c.configure(v); e != nil {
		t.Fatal(e)
	}
	done := make(chan struct{})
	go func() {
		defer close(done)
		for i := 0; i < 2000; i++ {
			if _, e := c.revealSecret(); e != nil {
				t.Error("reveal failed")
			}
		}
	}()
	for i := 0; i < 100; i++ {
		if e := c.configure(defaultConnectorInput()); e != nil {
			t.Fatal(e)
		}
	}
	<-done
}
