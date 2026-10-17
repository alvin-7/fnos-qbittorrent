package main

import (
	"bytes"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
	"time"
)

func TestConnectorPersistConflictAndNoReplay(t *testing.T) {
	writes := 0
	c := newConnector(t.TempDir(), http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { writes++; http.Error(w, "backend unavailable", 503) }))
	cfg := connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18982, Username: "fixture", Password: "isolated-test-password-42", AllowedCIDRs: []string{"127.0.0.1/32"}, TrustedHTTP: true}
	if e := c.configure(cfg); e != nil {
		t.Fatal(e)
	}
	occupied, e := net.Listen("tcp", "127.0.0.1:18983")
	if e != nil {
		t.Fatal(e)
	}
	defer occupied.Close()
	cfg.Port = 18983
	if c.configure(cfg) == nil {
		t.Fatal("conflict accepted")
	}
	if c.status().Port != 18982 {
		t.Fatal("partial configuration committed")
	}
	c.sessions["fixture"] = connectorSession{"127.0.0.1", time.Now().Add(time.Hour)}
	r := httptest.NewRequest("POST", "http://host.docker.internal:18982/api/v2/torrents/stop", nil)
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	r.AddCookie(&http.Cookie{Name: "SID", Value: "fixture"})
	r.RemoteAddr = "127.0.0.1:1"
	w := httptest.NewRecorder()
	c.ServeHTTP(w, r)
	if writes != 1 || w.Code != 503 {
		t.Fatal("mutation replay/failure hidden", writes, w.Code)
	}
	before, err := os.ReadFile(c.file())
	if err != nil {
		t.Fatal(err)
	}
	cfg.Port = 18983
	cfg.Password = ""
	assertConnectorReason(t, configureResponse(c, cfg), "connector_bind_failed")
	after, err := os.ReadFile(c.file())
	if err != nil || !bytes.Equal(before, after) || len(c.sessions) != 1 || !c.status().Listening {
		t.Fatal("failed save changed old configuration or sessions")
	}
	cfg.Port = 18982
	cfg.Enabled = false
	if e := c.configure(cfg); e != nil {
		t.Fatal(e)
	}
	if len(c.sessions) != 0 || c.status().Listening {
		t.Fatal("disable did not revoke")
	}
	cfg.Enabled = true
	if e := c.configure(cfg); e != nil {
		t.Fatal(e)
	}
	if len(c.sessions) != 0 {
		t.Fatal("enable resurrected sessions")
	}
	c.close()
	restored := newConnector(c.dir, nil)
	if e := restored.load(); e != nil {
		t.Fatal(e)
	}
	defer restored.close()
	if !restored.status().Listening || restored.status().Port != 18982 {
		t.Fatal("persisted listener not restored")
	}
	if len(restored.sessions) != 0 {
		t.Fatal("session resurrected")
	}
}
