package main

import (
	"context"
	"net/http"
	"net"
 "time"
 "io"
 "net/http/httptest"
	"testing"
 "os"
 "path/filepath"
 "encoding/json"
 "strings"
 "fmt"
 "syscall"
 )

type mockDirectoryProvider struct{ paths []string; denied string; failed bool }
func(p *mockDirectoryProvider)Roots(context.Context)([]string,error){if p.failed{return nil,errSource};return p.paths,nil}
func(p *mockDirectoryProvider)ACL(_ context.Context,_ string,paths []string)([]directoryACL,error){a:=[]directoryACL{};for _,path:=range paths{a=append(a,directoryACL{path,path!=p.denied,path!=p.denied})};return a,nil}
func directoryCall(s *directoryService,action string,q any)*httptest.ResponseRecorder{b,_:=json.Marshal(q);r:=httptest.NewRequest("POST",prefix+"/gateway/directories/"+action,strings.NewReader(string(b)));r.Header.Set("X-Trim-Userid","1000");w:=httptest.NewRecorder();s.ServeHTTP(w,r);return w}
func TestDirectoryRealFilesystem(t *testing.T){
 base:=t.TempDir();root:=filepath.Join(base,"授权目录");outside:=filepath.Join(base,"not-authorized-secret");os.Mkdir(root,0700);os.Mkdir(outside,0700);os.Mkdir(filepath.Join(root,"中文 🎬"),0700);os.WriteFile(filepath.Join(root,"file-not-directory"),[]byte("x"),0600);os.Symlink(outside,filepath.Join(root,"escape"))
 p:=&mockDirectoryProvider{paths:[]string{root}};s:=newDirectoryService(p)
 w:=directoryCall(s,"roots",map[string]any{});if w.Code!=200{t.Fatal(w.Code,w.Body.String())};var d struct{Roots []directoryRoot;AuthorizationRevision string};json.Unmarshal(w.Body.Bytes(),&d);if len(d.Roots)!=1{t.Fatal(w.Body.String())};id:=d.Roots[0].RootID
 w=directoryCall(s,"browse",map[string]any{"rootId":id,"relativePath":""});if w.Code!=200||!strings.Contains(w.Body.String(),"中文")||strings.Contains(w.Body.String(),"escape")||strings.Contains(w.Body.String(),"file-not-directory")||strings.Contains(w.Body.String(),outside){t.Fatal(w.Code,w.Body.String())}
 for _,path:=range []string{outside,root+"/../not-authorized-secret",root+"/escape",root+"/%252e%252e"}{w=directoryCall(s,"validate",map[string]any{"manualPath":path});if w.Code!=404{t.Fatal(path,w.Code,w.Body.String())}}
 p.paths=nil;w=directoryCall(s,"validate",map[string]any{"manualPath":root});if w.Code!=404{t.Fatal("revocation",w.Code)}
 p.failed=true;w=directoryCall(s,"roots",map[string]any{});if w.Code!=503{t.Fatal(w.Code)}
}
func TestDirectoryParentTraverseOnlyFinalReadable(t *testing.T) {
	base := t.TempDir()
	parent := filepath.Join(base, "traverse-only")
	root := filepath.Join(parent, "authorized")
	if err := os.Mkdir(parent, 0700); err != nil { t.Fatal(err) }
	if err := os.Mkdir(root, 0700); err != nil { t.Fatal(err) }
	if _, err := os.Create(filepath.Join(root, "visible.txt")); err != nil { t.Fatal(err) }
	if err := os.Chmod(parent, 0111); err != nil { t.Fatal(err) }
	defer os.Chmod(parent, 0700)
	if _, err := os.ReadDir(parent); !os.IsPermission(err) { t.Fatalf("fixture must deny ancestor enumeration, uid=%d err=%v", os.Geteuid(), err) }
	got, err := directoryOpen(root)
	if err != nil { t.Fatalf("final authorized root must open when ancestors are traverse-only: %v", err) }
	defer syscall.Close(got)
	var entries []string
	buf := make([]byte, 4096)
	for { n, e := syscall.ReadDirent(got, buf); if e != nil { t.Fatal(e) }; if n == 0 { break }; entries = append(entries, "readable") }
	if len(entries) == 0 { t.Fatal("final authorized root was not enumerable") }
}

func TestDirectoryPaging(t *testing.T){
 root:=t.TempDir();for i:=0;i<225;i++{os.Mkdir(filepath.Join(root,fmt.Sprintf("dir-%03d",i)),0700)}
 s:=newDirectoryService(&mockDirectoryProvider{paths:[]string{root}});roots,_,e:=s.roots(context.Background(),"1000");if e!=nil||len(roots)!=1{t.Fatal(e,roots)}
 cursor:="";seen:=map[string]bool{};for page:=0;page<10;page++{w:=directoryCall(s,"browse",map[string]any{"rootId":roots[0].RootID,"relativePath":"","cursor":cursor});if w.Code!=200{t.Fatal(w.Code,w.Body.String())};var d struct{Entries []directoryEntry;NextCursor string};json.Unmarshal(w.Body.Bytes(),&d);if len(d.Entries)>100{t.Fatal("unbounded page")};for _,v:=range d.Entries{seen[v.Name]=true};cursor=d.NextCursor;if cursor==""{break}}
 if len(seen)!=225{t.Fatalf("got %d directories",len(seen))}
}


func TestConnectorDirectoryIsolation(t *testing.T){
 calls:=0;c:=newConnector(t.TempDir(),http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){calls++;io.WriteString(w,"ok")}));c.cfg=connectorConfig{connectorInput:connectorInput{Enabled:true,BindIP:"127.0.0.1",Port:18081,AllowedCIDRs:[]string{"127.0.0.1/32"}}};c.listener,_=net.Listen("tcp","127.0.0.1:0");defer c.listener.Close();c.sessions["fixture"]=connectorSession{"127.0.0.1",time.Now().Add(time.Hour)}
 for _,method:=range []string{"GET","POST"}{for _,path:=range []string{"/api/v2/app/getDirectoryContent","/api/v2/app/GetDirectoryContent","/api/v2/app/%67etDirectoryContent","/gateway/directories/roots"}{r:=httptest.NewRequest(method,"http://host.docker.internal:18081"+path,nil);r.RemoteAddr="127.0.0.1:1";r.Header.Set("Cookie","SID=fixture");w:=httptest.NewRecorder();c.ServeHTTP(w,r);if w.Code<400||calls!=0{t.Fatal(path,w.Code,calls)}}}
 r:=httptest.NewRequest("GET","http://host.docker.internal:18081/api/v2/app/version",nil);r.RemoteAddr="127.0.0.1:1";r.Header.Set("Cookie","SID=fixture");w:=httptest.NewRecorder();c.ServeHTTP(w,r);if w.Code!=200||calls!=1{t.Fatal("transparent business API broken",w.Code,calls)}
}
func TestDirectorySourceFailsClosed(t *testing.T) {
	t.Setenv("TRIM_API_TOKEN", "")
	s := newDirectoryService(nil)
	r := httptest.NewRequest("POST", prefix+"/gateway/directories/roots", nil)
	r.Header.Set("X-Trim-Userid", "1000")
	w := httptest.NewRecorder()
	s.ServeHTTP(w, r)
	if w.Code != 503 {
		t.Fatalf("missing source should be 503, got %d", w.Code)
	}
}
func TestNativeUpstreamDirectoryForbidden(t *testing.T) {
	for _, method := range []string{"GET", "POST"} {
		reached := false
		h := nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { reached = true }))
		r := httptest.NewRequest(method, prefix+"/api/v2/app/getDirectoryContent", nil)
		r = r.WithContext(context.WithValue(r.Context(), gatewayUnixContextKey{}, true))
		r.Header.Set("X-Trim-Userid", "1000")
		r.Header.Set("X-Trim-Isadmin", "true")
		r.Header.Set("Origin", "http://example.com")
		r.Header.Set(csrfHeader, "gateway-request-v1")
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if reached || w.Code != 403 {
			t.Fatalf("%s browse forwarded=%v status=%d", method, reached, w.Code)
		}
	}
}
