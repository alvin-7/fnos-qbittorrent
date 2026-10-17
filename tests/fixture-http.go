package main
import("net/http";"os")
func main(){http.HandleFunc("/rss",func(w http.ResponseWriter,r *http.Request){if r.URL.RawQuery!="id=fixture&sign=LOCAL_TEST_ONLY"{http.Error(w,"invalid fixture",400);return};w.Header().Set("Content-Type","application/x-bittorrent");http.ServeFile(w,r,os.Args[1])});if err:=http.ListenAndServe(":8090",nil);err!=nil{panic(err)}}
