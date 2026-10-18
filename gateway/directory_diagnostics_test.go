package main

import (
 "context"
 "encoding/json"
 "net/http"
 "net/http/httptest"
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestDirectoryStageDiagnostics(t *testing.T) {
 t.Setenv("TRIM_API_TOKEN", "test-only-secret")
 for _,stage:=range []string{"shared_grants","user_acl"} { t.Run(stage,func(t *testing.T){
  server:=httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){
   var q struct{Req string};json.NewDecoder(r.Body).Decode(&q)
   if stage=="user_acl"&&q.Req=="trim.file.getSharedAccessibleFolders" {json.NewEncoder(w).Encode(map[string]any{"code":0,"data":map[string]any{"paths":[]string{"/fixture/private-sensitive"}}});return}
   w.Write([]byte(`{"code":200003,"msg":"/secret/raw-platform test-only-secret"}`))
  }));defer server.Close()
  s:=newDirectoryService(&fnosDirectoryProvider{client:&http.Client{Transport:contractTransport{server.URL}}})
  w:=directoryCall(s,"roots",map[string]any{});var d struct{Code string;Diagnostics struct{Stage string;Counts map[string]int}};json.Unmarshal(w.Body.Bytes(),&d)
  if w.Code!=503||d.Code!="AUTH_SCOPE_DENIED"||d.Diagnostics.Stage!=stage {t.Fatalf("missing safe stage: %s",w.Body.String())}
  if d.Diagnostics.Counts["discovered"]!=map[string]int{"shared_grants":0,"user_acl":1}[stage] {t.Fatal(w.Body.String())}
  for _,secret:=range []string{"/fixture","/secret","raw-platform","test-only-secret"}{if strings.Contains(w.Body.String(),secret){t.Fatal("diagnostic disclosure")}}
 }) }
}
func TestDirectoryFilesystemReasons(t *testing.T){
 base:=t.TempDir();denied:=filepath.Join(base,"denied");os.Mkdir(denied,0000);defer os.Chmod(denied,0700)
 for _,tc:=range []struct{path,reason,count string}{{filepath.Join(base,"missing"),"AUTH_MOUNT_UNAVAILABLE","mountUnavailable"},{denied,"AUTH_PACKAGE_READ_DENIED","packageReadDenied"}} {
  if os.Getuid()==0&&tc.count=="packageReadDenied"{continue}
  s:=newDirectoryService(&mockDirectoryProvider{paths:[]string{tc.path}});w:=directoryCall(s,"roots",map[string]any{});var d struct{Code string;Diagnostics struct{Counts map[string]int}};json.Unmarshal(w.Body.Bytes(),&d)
  if d.Code!=tc.reason||d.Diagnostics.Counts[tc.count]!=1||d.Diagnostics.Counts["discovered"]!=1 {t.Fatal(w.Body.String())}
 }
 _=context.Background()
}
