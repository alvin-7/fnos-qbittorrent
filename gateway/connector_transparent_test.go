package main

import (
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestConnectorTransparentStandardAPI(t *testing.T) {
	calls := 0
	c := newConnector(t.TempDir(), http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		calls++
		b, _ := io.ReadAll(r.Body)
		if r.Method != "POST" || r.URL.RawQuery != "extra=1" || string(b) != "new_parameter=%FF&json=%7B%7D" {
			t.Error("request transformed", r.Method, r.URL.RawQuery, string(b))
		}
		w.Header().Set("Content-Type", "application/json")
		w.Header().Set("Set-Cookie", "backend=secret")
		w.WriteHeader(409)
		w.Write([]byte(`{"qb":"original"}`))
	}))
	c.cfg = connectorConfig{connectorInput: connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18081, AllowedCIDRs: []string{"127.0.0.1/32"}}}
	c.listener, _ = net.Listen("tcp", "127.0.0.1:0")
	defer c.listener.Close()
	c.sessions["fixture"] = connectorSession{"127.0.0.1", time.Now().Add(time.Hour)}
	r := httptest.NewRequest("POST", "http://host.docker.internal:18081/api/v2/app/setPreferences?extra=1", strings.NewReader("new_parameter=%FF&json=%7B%7D"))
	r.Header.Set("Cookie", "SID=fixture")
	r.RemoteAddr = "127.0.0.1:1"
	w := httptest.NewRecorder()
	c.ServeHTTP(w, r)
	if w.Code != 409 || w.Body.String() != `{"qb":"original"}` || calls != 1 {
		t.Fatal("not transparent", w.Code, w.Body.String(), calls)
	}
	if w.Header().Get("Set-Cookie") != "" {
		t.Fatal("backend cookie leaked")
	}
}
