package main

// Test-only contract transport. No provider override is shipped in the FPK.
import("context";"encoding/json";"net";"net/http";"os";"path/filepath";"testing")
func TestDirectory153Server(t *testing.T){
 file:=os.Getenv("DIRECTORY153_ROOTS");if file==""{t.Skip("isolated local fixture")}
 p:=newFnosDirectoryProvider()
 p.client=&http.Client{Transport:&http.Transport{DialContext:func(ctx context.Context,_,_ string)(net.Conn,error){return (&net.Dialer{}).DialContext(ctx,"unix",os.Getenv("DIRECTORY153_PLATFORM_SOCKET"))}}}
 s:=newDirectoryService(p);proxy,e:=newProxy(os.Getenv("BACKEND_URL"));if e!=nil{t.Fatal(e)}
 ln,e:=net.Listen("unix",os.Getenv("GATEWAY_SOCKET"));if e!=nil{t.Fatal(e)};defer ln.Close()
 c:=newConnector(filepath.Join(filepath.Dir(file),"connector"),proxy);defer c.close()
 a:=newSiteAnalysis(proxy)
 h:=nativeGatewayHandler(http.HandlerFunc(func(w http.ResponseWriter,r *http.Request){if r.URL.Path==prefix+"/api/v2/gateway/analysis/sites"{a.ServeHTTP(w,r);return};if len(r.URL.Path)>=len(prefix+"/gateway/directories/")&&r.URL.Path[:len(prefix+"/gateway/directories/")]==prefix+"/gateway/directories/"{s.ServeHTTP(w,r);return};if s.guard(proxy,w,r){proxy.ServeHTTP(w,r)}}))
 _=json.Valid
 server:=&http.Server{Handler:h,ConnContext:gatewayConnectionContext};t.Fatal(server.Serve(ln))
}
