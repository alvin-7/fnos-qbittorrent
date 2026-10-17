// fnOS gateway adapter for qBittorrent. It accepts only the private Unix socket.
package main

import (
	"log"
	"net"
	"net/http"
	"net/http/httputil"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const prefix = "/app/fnos-qbittorrent"

func newProxy(backendURL string) (*httputil.ReverseProxy, error) {
	backend, err := url.Parse(backendURL)
	if err != nil || backend.Scheme == "" || backend.Host == "" {
		if err == nil {
			err = &url.Error{Op: "parse", URL: backendURL, Err: os.ErrInvalid}
		}
		return nil, err
	}
	proxy := httputil.NewSingleHostReverseProxy(backend)
	proxy.Director = func(r *http.Request) {
		// The gateway owns the external prefix; qB receives its normal root paths.
		r.URL.Path = strings.TrimPrefix(r.URL.Path, prefix)
		if r.URL.Path == "" {
			r.URL.Path = "/"
		}
		r.URL.RawPath = ""
		// Keep URL.Host as the Docker service address: this is where the transport
		// dials. Changing it to loopback would dial the gateway container itself.
		r.URL.Scheme, r.URL.Host = backend.Scheme, backend.Host
		// Never forward application credentials, including on static navigation.
		r.Header.Del(csrfHeader)
		r.Header.Del("X-Fnos-Bootstrap")
		var backendCookies []string
		for _, c := range r.Cookies() {
			if c.Name != sessionCookie {
				backendCookies = append(backendCookies, c.String())
			}
		}
		r.Header.Del("Cookie")
		if len(backendCookies) > 0 {
			r.Header.Set("Cookie", strings.Join(backendCookies, "; "))
		}
		// Never forward client-supplied identity headers to qB.
		for _, h := range []string{"X-Trim-Userid", "X-Trim-Isadmin", "X-Trim-Username"} {
			r.Header.Del(h)
		}
		// Only called after gatewayHandler validates the original browser origin.
		// qB independently keeps its Host/CSRF checks against this backend origin.
		if r.Header.Get("Origin") != "" {
			r.Header.Set("Origin", "http://127.0.0.1:18080")
		}
		if r.Header.Get("Referer") != "" {
			r.Header.Set("Referer", "http://127.0.0.1:18080/")
		}
		for h := range r.Header {
			if strings.HasPrefix(strings.ToLower(h), "x-trim-") || strings.HasPrefix(strings.ToLower(h), "x-forwarded-") || strings.EqualFold(h, "Forwarded") {
				r.Header.Del(h)
			}
		}
		r.Host = "127.0.0.1:18080"
	}
	if file := os.Getenv("BACKEND_PASSWORD_FILE"); file != "" {
		proxy.Transport = &nativeTransport{base: &http.Transport{ResponseHeaderTimeout: 5 * time.Second, DialContext: (&net.Dialer{Timeout: 3 * time.Second}).DialContext}, backend: strings.TrimRight(backendURL, "/"), passwordFile: file, cookie: os.Getenv("BACKEND_COOKIE")}
	}
	proxy.ModifyResponse = func(res *http.Response) error {
		for h := range res.Header {
			if strings.HasPrefix(strings.ToLower(h), "access-control-") || strings.HasPrefix(strings.ToLower(h), "x-trim-") {
				res.Header.Del(h)
			}
		}
		if res.StatusCode == 403 {
			reason := res.Header.Get("X-Fnos-Gateway-Reason")
			if reason != "native_policy_forbidden" {
				reason = "backend_403"
			}
			res.Header.Set("X-Fnos-Gateway-Reason", reason)
			log.Printf("gateway reject stage=backend reason=%s", reason)
		}
		return nil
	}
	return proxy, nil
}

func main() {
	socket := os.Getenv("GATEWAY_SOCKET")
	if socket == "" {
		socket = "/app/app.sock"
	}
	if err := os.MkdirAll(filepath.Dir(socket), 0770); err != nil {
		log.Fatal(err)
	}
	if err := os.Chmod(filepath.Dir(socket), 0770); err != nil {
		log.Fatal(err)
	}
	_ = os.Remove(socket)
	backendURL := os.Getenv("BACKEND_URL")
	if backendURL == "" {
		backendURL = "http://qbittorrent:18080"
	}
	proxy, err := newProxy(backendURL)
	if err != nil {
		log.Fatal(err)
	}
	proxy.ErrorHandler = func(w http.ResponseWriter, _ *http.Request, err error) {
		http.Error(w, "gateway backend unavailable", 502)
		log.Printf("proxy backend transport failed")
	}
	ln, err := net.Listen("unix", socket)
	if err != nil {
		log.Fatal(err)
	}
	defer ln.Close()
	if err := os.Chmod(socket, 0660); err != nil {
		log.Fatal(err)
	}
	log.Printf("listening on %s", socket)
	handler := gatewayHandler(proxy)
	if file := os.Getenv("BACKEND_PASSWORD_FILE"); file != "" {
		connector := newConnector(filepath.Join(filepath.Dir(file), "moviepilot-private"), proxy)
		if err := connector.load(); err != nil {
			log.Printf("connector startup unavailable; configuration requires review")
		}
		defer connector.close()
		routed := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if strings.HasPrefix(r.URL.Path, prefix+"/api/v2/connector/") {
				connector.management(w, r)
				return
			}
			proxy.ServeHTTP(w, r)
		})
		handler = nativeGatewayHandler(routed)
	}
	server := &http.Server{Handler: handler, ConnContext: gatewayConnectionContext, ReadHeaderTimeout: 10 * time.Second, ReadTimeout: 60 * time.Second, WriteTimeout: 60 * time.Second, IdleTimeout: 60 * time.Second, MaxHeaderBytes: 32 << 10}
	if err := server.Serve(ln); err != nil {
		log.Fatal(err)
	}
}
