package main

// Raw qB messages are transient server-only data. Never log or echo them.
import (
	"encoding/json"
	"io"
	"net/http"
	"regexp"
	"strings"
	"time"
)

type qbLog struct {
	ID        int64  `json:"id"`
	Timestamp int64  `json:"timestamp"`
	Type      int    `json:"type"`
	Message   string `json:"message"`
}
type safeAddLog struct {
	Time        int64  `json:"time"`
	Category    string `json:"category"`
	Code        string `json:"code"`
	NumericCode *int   `json:"numeric_code,omitempty"`
	Message     string `json:"message"`
	Association string `json:"association"`
}
type diagnosticCursor struct {
	ID      int64
	Since   int64
	Expires time.Time
}

var diagnosticURL = regexp.MustCompile(`(?i)(?:https?|ftp)://[^\s<>]+`)

func classifyAddLog(l qbLog) safeAddLog {
	d := safeAddLog{Time: l.Timestamp, Category: "未知", Code: "UNKNOWN", Message: "未知错误，未输出原始日志", Association: "该时段后台错误，关联未确认"}
	// Only classify acquisition/parsing messages; URL and Source text cannot supply signatures.
	lower := strings.ToLower(diagnosticURL.ReplaceAllString(l.Message, ""))
	if !strings.HasPrefix(lower, "failed to add torrent.") && !strings.HasPrefix(lower, "failed to download torrent.") && !strings.HasPrefix(lower, "failed to load torrent.") {
		return d
	}
	i := strings.Index(lower, "reason:")
	if i < 0 {
		return d
	}
	reason := lower[i+7:]
	switch {
	case strings.Contains(reason, "expected value (list, dict, int or string) in bencoded string") && strings.Contains(reason, "[bdecode:4]"):
		d.Category = "INVALID_TORRENT"
		d.Code = "BENCODE_PARSE_ERROR"
		code := 4
		d.NumericCode = &code
		d.Message = "返回内容不是有效种子（bdecode:4），可能为站点错误响应，具体响应未知"
	case strings.Contains(reason, "host not found"), strings.Contains(reason, "hostname lookup"), strings.Contains(reason, "temporary failure in name resolution"):
		d.Category = "DNS"
		d.Code = "DNS_LOOKUP_FAILED"
		d.Message = "域名解析失败；请检查 NAS DNS 与网络。"
	case strings.Contains(reason, "ssl handshake failed"), strings.Contains(reason, "tls handshake"), strings.Contains(reason, "certificate verify failed"):
		d.Category = "TLS"
		d.Code = "TLS_FAILED"
		d.Message = "TLS 校验或握手失败；请检查系统时间、证书与代理。"
	case strings.Contains(reason, "server replied: not found"), strings.Contains(reason, "not found") && strings.Contains(reason, "404"):
		d.Category = "HTTP"
		d.Code = "HTTP_404"
		d.Message = "HTTP 404；请确认下载链接仍有效。"
	case strings.Contains(reason, "server replied: forbidden"):
		d.Category = "HTTP"
		d.Code = "HTTP_403"
		d.Message = "HTTP 403；请检查站点授权与链接有效性。"
	case strings.Contains(reason, "server replied: unauthorized"):
		d.Category = "HTTP"
		d.Code = "HTTP_401"
		d.Message = "HTTP 401；请检查站点授权。"
	case strings.Contains(reason, "invalid bencoding"), strings.Contains(reason, "invalid torrent"), strings.Contains(reason, "not a valid torrent"), strings.Contains(reason, "expected value (list, dict, int or string) in bencoded string"):
		d.Category = "非torrent"
		d.Code = "INVALID_TORRENT"
		d.Message = "返回内容不是有效种子；请检查是否返回登录页或错误页。"
	}
	return d
}
func (t *nativeTransport) readDiagnosticLogs(r *http.Request) ([]qbLog, bool) {
	q, e := http.NewRequestWithContext(r.Context(), "GET", t.backend+"/api/v2/log/main?normal=false&info=false&warning=true&critical=true&last_known_id=-1", nil)
	if e != nil {
		return nil, false
	}
	q.Host = "127.0.0.1:18080"
	q.Header.Set("Cookie", t.cookie)
	res, e := t.base.RoundTrip(q)
	if e != nil {
		return nil, false
	}
	defer res.Body.Close()
	if res.StatusCode != 200 {
		return nil, false
	}
	b, e := io.ReadAll(io.LimitReader(res.Body, (4<<20)+1))
	if e != nil || len(b) > 4<<20 {
		return nil, false
	}
	var logs []qbLog
	if json.Unmarshal(b, &logs) != nil {
		return nil, false
	}
	return logs, true
}
func diagnosticResponse(v any) *http.Response {
	b, _ := json.Marshal(v)
	return &http.Response{StatusCode: 200, Header: http.Header{"Content-Type": {"application/json"}, "Cache-Control": {"no-store"}}, Body: io.NopCloser(strings.NewReader(string(b)))}
}
func (t *nativeTransport) addDiagnostics(r *http.Request) *http.Response {
	if r.Method != "GET" || r.ContentLength > 0 {
		return nativeResponse(405)
	}
	q := r.URL.Query()
	for k, v := range q {
		if k != "cursor" || len(v) != 1 {
			return nativeResponse(400)
		}
	}
	now := time.Now()
	if t.diagnostics == nil {
		t.diagnostics = make(map[string]diagnosticCursor)
	}
	for k, v := range t.diagnostics {
		if now.After(v.Expires) {
			delete(t.diagnostics, k)
		}
	}
	cursor := q.Get("cursor")
	base, exists := t.diagnostics[cursor]
	if cursor != "" && !exists {
		return diagnosticResponse(map[string]any{"status": "unknown", "message": "诊断窗口已失效，状态未知", "events": []safeAddLog{}})
	}
	logs, ok := t.readDiagnosticLogs(r)
	if !ok {
		return diagnosticResponse(map[string]any{"status": "unknown", "message": "诊断不可用，状态未知；未输出原始日志", "events": []safeAddLog{}})
	}
	if cursor == "" {
		if len(t.diagnostics) >= 128 {
			return nativeResponse(503)
		}
		id := int64(-1)
		for _, l := range logs {
			if l.ID > id {
				id = l.ID
			}
		}
		key, e := randomSecret()
		if e != nil {
			return nativeResponse(503)
		}
		t.diagnostics[key] = diagnosticCursor{ID: id, Since: now.Unix(), Expires: now.Add(10 * time.Minute)}
		return diagnosticResponse(map[string]any{"status": "ready", "cursor": key})
	}
	events := []safeAddLog{}
	for _, l := range logs {
		if l.ID > base.ID && l.Timestamp >= base.Since && (l.Type == 4 || l.Type == 8) {
			events = append(events, classifyAddLog(l))
			if len(events) == 20 {
				break
			}
		}
	}
	return diagnosticResponse(map[string]any{"status": "unconfirmed", "message": "该时段后台错误，关联未确认；无日志不代表添加成功", "events": events})
}
