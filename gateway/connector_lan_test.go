package main

import (
	"net"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestConnectorLANMinimalConfig(t *testing.T) {
	c := newConnector(t.TempDir(), nil)
	defer c.close()
	v := connectorInput{Enabled: true, Port: 18985, Username: "fixture"}
	if c.configure(v) == nil {
		t.Fatal("empty password accepted")
	}
	v.Password = "isolated-fixture-password"
	if e := c.configure(v); e != nil {
		t.Fatal("minimal LAN config rejected", e)
	}
	a := c.listener.Addr().(*net.TCPAddr)
	if !a.IP.IsUnspecified() || a.Port != 18985 {
		t.Fatal(a)
	}
	if c.status().BindIP != "0.0.0.0" {
		t.Fatal("wrong default")
	}
	r := httptest.NewRequest("GET", "http://host.docker.internal:18985/api/v2/app/version", nil)
	r.RemoteAddr = "203.0.113.1:1234"
	w := httptest.NewRecorder()
	c.ServeHTTP(w, r)
	if w.Code != http.StatusForbidden {
		t.Fatal("unauthenticated access", w.Code)
	}
}
