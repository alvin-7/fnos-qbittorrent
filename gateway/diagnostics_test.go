package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func TestSafeClassification(t *testing.T) {
	cases := []struct{ msg, cat, code string }{
		{`Failed to download torrent. Source: "https://u:SECRET@private/path?passkey=TOKEN". Reason: "Host not found"`, "DNS", "DNS_LOOKUP_FAILED"},
		{`Failed to download torrent. Source: "https://SECRET/TOKEN". Reason: "SSL handshake failed"`, "TLS", "TLS_FAILED"},
		{`Failed to download torrent. Source: "https://SECRET/TOKEN". Reason: "Error transferring https://SECRET/TOKEN - server replied: Not Found"`, "HTTP", "HTTP_404"},
		{`Failed to load torrent. Source: "https://SECRET/TOKEN". Reason: "invalid bencoding"`, "非torrent", "INVALID_TORRENT"},
		{`Failed to download torrent. Source: "https://SECRET/Host-not-found/404". Reason: "opaque SECRET TOKEN"`, "未知", "UNKNOWN"},
	}
	for _, c := range cases {
		d := classifyAddLog(qbLog{Timestamp: 123, Message: c.msg})
		b, _ := json.Marshal(d)
		if d.Category != c.cat || d.Code != c.code {
			t.Errorf("classification got %s/%s expected %s/%s", d.Category, d.Code, c.cat, c.code)
		}
		for _, s := range []string{"SECRET", "TOKEN", "https:", "Source:", "Reason:"} {
			if strings.Contains(string(b), s) {
				t.Fatal("unsafe output")
			}
		}
	}
}
