package main

import (
	"context"
	"io"
	"net"
	"net/http"
	"path/filepath"
	"testing"
)

func TestNativeGatewayCookieFreeUnix(t *testing.T) {
	calls := 0
	h := nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { calls++; w.WriteHeader(204) }))
	ln, e := net.Listen("unix", filepath.Join(t.TempDir(), "app.sock"))
	if e != nil {
		t.Fatal(e)
	}
	srv := &http.Server{Handler: h, ConnContext: gatewayConnectionContext}
	go srv.Serve(ln)
	defer srv.Close()
	c := &http.Client{Transport: &http.Transport{DialContext: func(ctx context.Context, _, _ string) (net.Conn, error) {
		return (&net.Dialer{}).DialContext(ctx, "unix", ln.Addr().String())
	}}}
	for _, method := range []string{"GET", "POST"} {
		r, _ := http.NewRequest(method, "http://internal"+prefix+"/api/v2/torrents/info", nil)
		r.Header.Set("X-Trim-Userid", "1000")
		r.Header.Set("X-Trim-Isadmin", "true")
		r.Header.Set("Referer", "https://mobile.invalid/")
		r.Header.Set("X-Fnos-CSRF", "gateway-request-v1")
		res, e := c.Do(r)
		if e != nil {
			t.Fatal(e)
		}
		io.Copy(io.Discard, res.Body)
		res.Body.Close()
		if res.StatusCode != 204 {
			t.Fatalf("cookie-free %s: %d", method, res.StatusCode)
		}
	}
	if calls != 2 {
		t.Fatal(calls)
	}
}
