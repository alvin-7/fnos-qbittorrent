package main

import (
 "context"
 "encoding/json"
 "fmt"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "testing"
)

func TestDirectoryOfficialErrorReasons(t *testing.T) {
 t.Setenv("TRIM_API_TOKEN","test-only")
 for _,tc:=range []struct{status int;body,reason string}{
 {401,`{"code":200004}`,"AUTH_TOKEN_REJECTED"},
 {403,`{"code":200003}`,"AUTH_SCOPE_DENIED"},
 {404,`{"code":200005}`,"AUTH_API_UNAVAILABLE"},
 {200,`{"code":200001}`,"AUTH_REQUEST_INVALID"},
 {200,`{"code":0,"data":{"paths":"wrong"}}`,"AUTH_RESPONSE_INVALID"},
 {200,`{"code":0,"data":{}}`,"AUTH_RESPONSE_INVALID"},
 {200,`{"code":0,"data":null}`,"AUTH_RESPONSE_INVALID"},
 } {t.Run(tc.reason,func(t *testing.T){
  server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){w.WriteHeader(tc.status);fmt.Fprint(w,tc.body)}));defer server.Close()
  p:=&fnosDirectoryProvider{client:&http.Client{Transport:contractTransport{server.URL}}}
  _,e:=p.Roots(context.Background());w:=httptest.NewRecorder();directoryError(w,e)
  var d map[string]any;json.Unmarshal(w.Body.Bytes(),&d);if d["code"]!=tc.reason {t.Fatalf("got %s",w.Body.String())}
 })}
}
// The production provider still constructs its real request; only network transport is test-only.
type contractTransport struct{url string}
func(c contractTransport)RoundTrip(r *http.Request)(*http.Response,error){q:=r.Clone(r.Context());u,_:=http.NewRequest(r.Method,c.url,r.Body);q.URL.Host=u.URL.Host;q.URL.Scheme=u.URL.Scheme;return http.DefaultTransport.RoundTrip(q)}

func TestDirectoryOfficialThreeGrantContract(t *testing.T) {
 t.Setenv("TRIM_API_TOKEN","test-only")
 base:=t.TempDir();roots:=[]string{filepath.Join(base,"vol1","授权 空格"),filepath.Join(base,"vol2","电影"),filepath.Join(base,"vol3","qBittorrent"),filepath.Join(base,"vol2","qBittorrent")}
 for _,r:=range roots{if e:=os.MkdirAll(filepath.Join(r,"子目录"),0700);e!=nil{t.Fatal(e)}}
 hidden:=filepath.Join(base,"not-authorized-secret");os.Mkdir(hidden,0700)
 server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
  var q struct{AppName,Req string;Data struct{UID int;Path []string}}
  if json.NewDecoder(r.Body).Decode(&q)!=nil||q.AppName!=directoryApp||r.URL.Path!="/api/v1/trimapp"||r.Header.Get("Authorization")!="Bearer test-only"{t.Error("bad official request");w.WriteHeader(400);return}
  if q.Req=="trim.file.getSharedAccessibleFolders"{json.NewEncoder(w).Encode(map[string]any{"code":0,"data":map[string]any{"paths":roots}});return}
  if q.Req!="trim.file.checkUserACL"||q.Data.UID!=1000{t.Error("bad current user ACL request");w.WriteHeader(400);return}
  a:=[]directoryACL{};for _,p:=range q.Data.Path{a=append(a,directoryACL{p,true,true})};json.NewEncoder(w).Encode(map[string]any{"code":0,"data":a})
 }));defer server.Close()
 s:=newDirectoryService(&fnosDirectoryProvider{client:&http.Client{Transport:contractTransport{server.URL}}})
 w:=directoryCall(s,"roots",map[string]any{});var got struct{Roots []directoryRoot};json.Unmarshal(w.Body.Bytes(),&got)
 if w.Code!=200||len(got.Roots)!=4{t.Fatalf("three application grants lost: %d %s",w.Code,w.Body.String())}
 for _,root:=range roots{w=directoryCall(s,"validate",map[string]any{"manualPath":root+"/子目录"});if w.Code!=200{t.Fatal(w.Code,w.Body.String())}}
 w=directoryCall(s,"validate",map[string]any{"manualPath":hidden});if w.Code!=404{t.Fatal("unauthorized path returned")}
}
