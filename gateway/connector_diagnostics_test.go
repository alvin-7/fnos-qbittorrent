package main

import (
	"encoding/json"
	"net"
	"net/http/httptest"
	"net/url"
	"os"
	"strings"
	"testing"
)

func configureResponse(c *connector, v connectorInput) *httptest.ResponseRecorder {
	b, _ := json.Marshal(v)
	r := httptest.NewRequest("POST", "http://local"+prefix+"/api/v2/connector/configure", strings.NewReader(url.Values{"json": {string(b)}}.Encode()))
	r.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	w := httptest.NewRecorder()
	c.management(w, r)
	return w
}
func assertConnectorReason(t *testing.T, w *httptest.ResponseRecorder, want string) {
	t.Helper()
	var body map[string]string
	if w.Code != 409 || json.Unmarshal(w.Body.Bytes(), &body) != nil || body["reason"] != want || len(body) != 1 {
		t.Fatalf("expected safe JSON 409 %s, got %d %s", want, w.Code, w.Body.String())
	}
}
func TestConnectorInvalidAndStorageReasons(t *testing.T) {
	c := newConnector(t.TempDir(), nil)
	defer c.close()
	assertConnectorReason(t, configureResponse(c, connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18081, Username: "fixture", Password: strings.Repeat("x", 1025), AllowedCIDRs: []string{"127.0.0.1/32"}, TrustedHTTP: true}), "invalid_connector_scope_or_credentials")
	assertConnectorReason(t, configureResponse(c, connectorInput{Password: strings.Repeat("x", 1025)}), "invalid_connector_scope_or_credentials")
	// Actual filesystem permission failure as the unprivileged test process.
	parent := t.TempDir()
	if e := os.Chmod(parent, 0500); e != nil {
		t.Fatal(e)
	}
	defer os.Chmod(parent, 0700)
	locked := newConnector(parent+"/private", nil)
	assertConnectorReason(t, configureResponse(locked, connectorInput{}), "private_storage_permissions")
	if _, e := os.Stat(locked.file()); !os.IsNotExist(e) {
		t.Fatal("unwritable save created file")
	}
}
func TestConnectorSafeConflictReason(t *testing.T) {
	c := newConnector(t.TempDir(), nil)
	defer c.close()
	ln, e := net.Listen("tcp", "127.0.0.1:0")
	if e != nil {
		t.Fatal(e)
	}
	defer ln.Close()
	v := connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: ln.Addr().(*net.TCPAddr).Port, Username: "fixture", Password: strings.Repeat("x", 32), AllowedCIDRs: []string{"127.0.0.1/32"}, TrustedHTTP: true}
	assertConnectorReason(t, configureResponse(c, v), "connector_bind_failed")
	if c.status().Listening {
		t.Fatal("partial listener")
	}
	if _, e := os.Stat(c.file()); !os.IsNotExist(e) {
		t.Fatal("failed bind persisted configuration")
	}
}
