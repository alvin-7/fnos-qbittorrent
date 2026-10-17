package main

import (
	"bytes"
	"io"
	"mime/multipart"
	"net"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestConnectorMultipartAddPreservesBytes(t *testing.T) {
	var got []byte
	c := newConnector(t.TempDir(), http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { got, _ = io.ReadAll(r.Body) }))
	c.cfg = connectorConfig{connectorInput: connectorInput{Enabled: true, BindIP: "127.0.0.1", Port: 18081, AllowedCIDRs: []string{"127.0.0.1/32"}}}
	c.listener, _ = net.Listen("tcp", "127.0.0.1:0")
	defer c.listener.Close()
	c.sessions["fixture"] = connectorSession{"127.0.0.1", time.Now().Add(time.Hour)}
	var body bytes.Buffer
	m := multipart.NewWriter(&body)
	f, _ := m.CreateFormFile("torrents", "test.torrent")
	f.Write([]byte{0, 255, 128, 1})
	m.Close()
	original := append([]byte{}, body.Bytes()...)
	r := httptest.NewRequest("POST", "http://host.docker.internal:18081/api/v2/torrents/add", bytes.NewReader(original))
	r.Header.Set("Content-Type", m.FormDataContentType())
	r.Header.Set("Cookie", "SID=fixture")
	r.RemoteAddr = "127.0.0.1:1"
	w := httptest.NewRecorder()
	c.ServeHTTP(w, r)
	if w.Code != 200 || !bytes.Equal(got, original) {
		t.Fatal("multipart refused/corrupted", w.Code, strings.TrimSpace(w.Body.String()))
	}
}
