package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func Test116ExactBdecodeSignature(t *testing.T) {
	d := classifyAddLog(qbLog{Message: `Failed to add torrent. Source: "https://fixture.invalid/synthetic?token=CANARY". Reason: expected value (list, dict, int or string) in bencoded string [bdecode:4]`})
	if d.Code != "INVALID_TORRENT" && d.Code != "BENCODE_PARSE_ERROR" {
		t.Fatalf("1.1.6 exact signature not recognized: %s", d.Code)
	}
}
func TestBdecodeSafeStructuredCode(t *testing.T) {
	for _, source := range []string{`https://u:CANARY@fixture.invalid/CANARY?next=https://nested.invalid/CANARY`, `https://fixture.invalid/CANARY?next=https%3A%2F%2Fnested.invalid%2FCANARY`} {
		d := classifyAddLog(qbLog{Message: `Failed to add torrent. Source: "` + source + `". Reason: expected value (list, dict, int or string) in bencoded string [bdecode:4] https://reason.invalid/CANARY?next=https://nested.invalid/CANARY`})
		b, _ := json.Marshal(d)
		var v map[string]any
		json.Unmarshal(b, &v)
		if v["category"] != "INVALID_TORRENT" || v["code"] != "BENCODE_PARSE_ERROR" || v["numeric_code"] != float64(4) {
			t.Fatalf("structured fixed classification missing: %s", b)
		}
		for _, s := range []string{"CANARY", "fixture.invalid", "nested.invalid", "reason.invalid", "Source:", "Reason:", "https:", "expected value"} {
			if strings.Contains(string(b), s) {
				t.Fatal("unsafe output")
			}
		}
		if d.Message != "返回内容不是有效种子（bdecode:4），可能为站点错误响应，具体响应未知" {
			t.Fatal("fixed message missing")
		}
	}
}
