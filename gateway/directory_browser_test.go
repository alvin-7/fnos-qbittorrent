package main

// Test-only provider injection. This entry is compiled only into go test binary,
// never the FPK gateway. File-system operations run as the current package-like UID.
import("encoding/json";"net";"net/http";"os";"testing";"path/filepath")
func TestDirectoryBrowserServer(t *testing.T){
 file:=os.Getenv("DIRECTORY_TEST_ROOT_FILE");if file==""{t.Skip("test-only browser fixture")}
 b,e:=os.ReadFile(file);if e!=nil{t.Fatal(e)};var roots []string;if json.Unmarshal(b,&roots)!=nil{t.Fatal("roots")}
 s:=newDirectoryService(&mockDirectoryProvider{paths:roots});proxy,e:=newProxy(os.Getenv("BACKEND_URL"));if e!=nil{t.Fatal(e)}
 sock:=os.Getenv("GATEWAY_SOCKET");ln,e:=net.Listen("unix",sock);if e!=nil{t.Fatal(e)};defer ln.Close()
 c:=newConnector(filepath.Join(filepath.Dir(file),"connector"),proxy);defer c.close()
 h:=nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){if len(r.URL.Path)>=len(prefix+"/gateway/directories/")&&r.URL.Path[:len(prefix+"/gateway/directories/")]==prefix+"/gateway/directories/"{s.ServeHTTP(w,r);return};if s.guard(proxy,w,r){proxy.ServeHTTP(w,r)}}))
 server:=&http.Server{Handler:h,ConnContext:gatewayConnectionContext};t.Fatal(server.Serve(ln))
}
