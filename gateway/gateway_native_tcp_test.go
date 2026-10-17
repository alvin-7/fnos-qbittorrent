package main

import (
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestNativeGatewayRealTCPRejectsSpoofedIdentity(t *testing.T) {
	s := httptest.NewUnstartedServer(nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { t.Error("TCP forwarded") })))
	s.Config.ConnContext = gatewayConnectionContext
	s.Start()
	defer s.Close()
	r, _ := http.NewRequest("POST", s.URL+prefix+"/api/v2/torrents/delete", nil)
	r.Header.Set("X-Trim-Userid", "1000")
	r.Header.Set("X-Trim-Isadmin", "true")
	r.Header.Set("Origin", "https://mobile.invalid")
	r.Header.Set(csrfHeader, "gateway-request-v1")
	res, e := s.Client().Do(r)
	if e != nil {
		t.Fatal(e)
	}
	io.Copy(io.Discard, res.Body)
	res.Body.Close()
	if res.StatusCode != 403 || res.Header.Get("X-Fnos-Gateway-Reason") != "untrusted_gateway_transport" {
		t.Fatal(res.StatusCode)
	}
}
