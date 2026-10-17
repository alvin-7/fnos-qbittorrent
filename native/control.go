// Linux/amd64 native fnOS lifecycle. No shell process matching or system package dependencies.
package main
import("os";"os/exec";"path/filepath";"fmt";"encoding/json";"crypto/sha256";"encoding/hex";"syscall";"strconv";"strings";"time";"net";"net/http";"net/url";"io";"regexp";"context";"crypto/rand";"encoding/base64")
type Proc struct{ PID int; Start, Command, Exe string; UID uint32 }
type State struct{ QB, Gateway Proc; Cookie string }
var dest, data string
func must(err error){if err!=nil{panic(err)}}
func path(s string)string{return filepath.Join(data,s)}
func read(p string)string{b,e:=os.ReadFile(p);if e!=nil{return ""};return string(b)}
func info(pid int)(Proc,error){
 p:=Proc{PID:pid};base:=fmt.Sprintf("/proc/%d",pid);st:=read(base+"/stat");i:=strings.LastIndex(st,") ");if i<0{return p,fmt.Errorf("process vanished")};f:=strings.Fields(st[i+2:]);if len(f)<20||f[0]=="Z"{return p,fmt.Errorf("not live")};p.Start=f[19]
 b,e:=os.ReadFile(base+"/cmdline");if e!=nil{return p,e};h:=sha256.Sum256(b);p.Command=hex.EncodeToString(h[:]);p.Exe,e=os.Readlink(base+"/exe");if e!=nil{return p,e};s:=syscall.Stat_t{};e=syscall.Stat(base,&s);p.UID=s.Uid;return p,e
}
func owned(p Proc)bool{now,e:=info(p.PID);return e==nil&&p.PID>1&&p.UID==uint32(os.Getuid())&&now==p}
func save(s State){b,e:=json.Marshal(s);must(e);must(os.WriteFile(path("state.json.new"),b,0600));must(os.Rename(path("state.json.new"),path("state.json")))}
func load()State{s:=State{};json.Unmarshal([]byte(read(path("state.json"))),&s);return s}
func stopOne(p Proc)error{
 if !owned(p){return nil};fd,_,errno:=syscall.Syscall(434,uintptr(p.PID),0,0);if errno!=0{return fmt.Errorf("pidfd_open: %v (kernel support required)",errno)};defer syscall.Close(int(fd))
 if !owned(p){return nil};_,_,errno=syscall.Syscall6(424,fd,uintptr(syscall.SIGTERM),0,0,0,0);if errno!=0{return errno}
 end:=time.Now().Add(35*time.Second);for time.Now().Before(end){if !owned(p){return nil};time.Sleep(100*time.Millisecond)};return fmt.Errorf("stop timeout PID %d; retained state, no unsafe SIGKILL",p.PID)
}
func client()*http.Client{return &http.Client{Timeout:2*time.Second}}
func version(cookie string)bool{r,_:=http.NewRequest("GET","http://127.0.0.1:18080/api/v2/app/version",nil);r.Header.Set("Cookie",cookie);res,e:=client().Do(r);if e!=nil{return false};defer res.Body.Close();b,_:=io.ReadAll(res.Body);return res.StatusCode==200&&string(b)=="v5.2.4"}
func socketHealthy()bool{c:=&http.Client{Timeout:2*time.Second,Transport:&http.Transport{DialContext:func(ctx context.Context,_,_ string)(net.Conn,error){return (&net.Dialer{}).DialContext(ctx,"unix",filepath.Join(dest,"app.sock"))}}};r,e:=c.Get("http://localhost/app/fnos-qbittorrent-native/api/v2/app/version");if e!=nil{return false};defer r.Body.Close();io.Copy(io.Discard,r.Body);return r.StatusCode==403}
func prepare(){
 if os.Getuid()==0{panic("refusing root; configure run-as=package")};if os.Getenv("TRIM_UID")!=""&&os.Getenv("TRIM_UID")!=strconv.Itoa(os.Getuid()){panic("package UID mismatch")}
 share:=os.Getenv("TRIM_DATA_SHARE_PATHS");if share==""||strings.Contains(share,":")||!filepath.IsAbs(share)||strings.ContainsAny(share,"\r\n"){panic("one absolute authorized data-share required")}
 must(os.MkdirAll(filepath.Join(share,"incomplete"),0700));probe:=filepath.Join(share,".native-write-test");f,e:=os.OpenFile(probe,os.O_CREATE|os.O_EXCL|os.O_WRONLY,0600);must(e);f.Close();must(os.Remove(probe))
 dir:=path("profile/qBittorrent/config");must(os.MkdirAll(dir,0700));conf:=filepath.Join(dir,"qBittorrent.conf")
 if _,e:=os.Stat(conf);os.IsNotExist(e){
  // New ID only: never import Docker conf/resume or rewrite /downloads implicitly.
  ini:=fmt.Sprintf("[LegalNotice]\nAccepted=true\n[BitTorrent]\nSession\\DefaultSavePath=%s\nSession\\TempPath=%s\nSession\\TempPathEnabled=true\nSession\\Port=49160\nSession\\UseRandomPort=false\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\nSession\\GlobalMaxRatio=0.1\nSession\\ShareLimitAction=Stop\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Address=127.0.0.1\nWebUI\\Port=18080\nWebUI\\AlternativeUIEnabled=true\nWebUI\\RootFolder=%s\nWebUI\\HostHeaderValidation=true\nWebUI\\ServerDomains=127.0.0.1\nWebUI\\CSRFProtection=true\nWebUI\\ClickjackingProtection=true\nWebUI\\LocalHostAuth=true\nWebUI\\AuthSubnetWhitelistEnabled=false\nWebUI\\ReverseProxySupportEnabled=false\n",share,filepath.Join(share,"incomplete"),filepath.Join(dest,"webui"))
  must(os.WriteFile(conf,[]byte(ini),0600))
 }
 // Upgrade path: add missing qB ratio keys only; never overwrite existing user values.
 current:=read(conf);if !strings.Contains(current,"Session\\GlobalMaxRatio="){current=strings.Replace(current,"[BitTorrent]\n","[BitTorrent]\nSession\\GlobalMaxRatio=0.1\n",1)};if !strings.Contains(current,"Session\\ShareLimitAction="){current=strings.Replace(current,"Session\\GlobalMaxRatio=0.1\n","Session\\GlobalMaxRatio=0.1\nSession\\ShareLimitAction=Stop\n",1)};must(os.WriteFile(conf,[]byte(current),0600))
 values:=map[string]string{"Address":"127.0.0.1","Port":"18080","AlternativeUIEnabled":"true","RootFolder":filepath.Join(dest,"webui"),"HostHeaderValidation":"true","ServerDomains":"127.0.0.1","CSRFProtection":"true","ClickjackingProtection":"true","LocalHostAuth":"true","AuthSubnetWhitelistEnabled":"false","ReverseProxySupportEnabled":"false"}
 lines:=strings.Split(read(conf),"\n");out:=[]string{};section:=""
 for _,line:=range lines{if strings.HasPrefix(line,"["){section=line};skip:=false;if section=="[Preferences]"{for key:=range values{if strings.HasPrefix(line,"WebUI\\"+key+"="){skip=true;break}}};if !skip{out=append(out,line)}}
 // Qt INI merges repeated groups; write a single Preferences group instead.
 text:=strings.Join(out,"\n");insertion:="";for key,value:=range values{insertion+="WebUI\\"+key+"="+value+"\n"}
 if strings.Contains(text,"[Preferences]\n"){text=strings.Replace(text,"[Preferences]\n","[Preferences]\n"+insertion,1)}else{text+="\n[Preferences]\n"+insertion}
 must(os.WriteFile(conf,[]byte(text),0600))
}
func launch(args []string,env []string,log string)Proc{
 f,e:=os.OpenFile(path(log),os.O_CREATE|os.O_TRUNC|os.O_WRONLY,0600);must(e);defer f.Close();c:=exec.Command(args[0],args[1:]...);c.Stdout=f;c.Stderr=f;c.Stdin=nil;c.Env=env;c.SysProcAttr=&syscall.SysProcAttr{Setsid:true};must(c.Start());time.Sleep(100*time.Millisecond);p,e:=info(c.Process.Pid);must(e);must(c.Process.Release());return p
}
func login()string{
 if until,e:=strconv.ParseInt(strings.TrimSpace(read(path("login-cooldown"))),10,64);e==nil&&time.Now().Unix()<until{return ""}
 re:=regexp.MustCompile(`temporary password is provided for this session: (\S+)`);m:=re.FindStringSubmatch(read(path("qb.log")));password:=strings.TrimSpace(read(path("backend-password")));if password==""{if len(m)<2{return ""};password=m[1]}
 must(os.WriteFile(path("login-cooldown"),[]byte(strconv.FormatInt(time.Now().Add(time.Minute).Unix(),10)),0600))
 r,e:=client().PostForm("http://127.0.0.1:18080/api/v2/auth/login",url.Values{"username":{"admin"},"password":{password}});if e!=nil{os.Remove(path("login-cooldown"));return ""};defer r.Body.Close();io.Copy(io.Discard,r.Body);if r.StatusCode!=204&&r.StatusCode!=200{return ""};if len(r.Cookies())==1{c:=r.Cookies()[0];cookie:=c.Name+"="+c.Value;if version(cookie){os.Remove(path("login-cooldown"));return cookie}};return ""
}
func main(){
 defer func(){if r:=recover();r!=nil{msg:=fmt.Sprint(r);fmt.Fprintln(os.Stderr,msg);if p:=os.Getenv("TRIM_TEMP_LOGFILE");p!=""{os.WriteFile(p,[]byte(msg),0600)};os.Exit(1)}}()
 if len(os.Args)!=2{panic("expected start|stop|status|prepare")};dest=os.Getenv("TRIM_APPDEST");data=os.Getenv("TRIM_PKGVAR");if !filepath.IsAbs(dest)||!filepath.IsAbs(data){panic("TRIM_APPDEST/TRIM_PKGVAR required")};must(os.MkdirAll(data,0700));syscall.Umask(0077)
 lock,e:=os.OpenFile(path("control.lock"),os.O_CREATE|os.O_RDWR,0600);must(e);defer lock.Close();must(syscall.Flock(int(lock.Fd()),syscall.LOCK_EX|syscall.LOCK_NB));defer syscall.Flock(int(lock.Fd()),syscall.LOCK_UN)
 s:=load();switch os.Args[1]{
 case "prepare":prepare()
 case "status":if owned(s.QB)&&owned(s.Gateway)&&socketHealthy(){if version(s.Cookie){return};s.Cookie=login();if version(s.Cookie){save(s);return}};os.Exit(3)
 case "stop":must(stopOne(s.Gateway));must(stopOne(s.QB));must(os.RemoveAll(path("state.json")))
 case "start":
  prepare();if owned(s.QB)||owned(s.Gateway){if owned(s.QB)&&owned(s.Gateway)&&version(s.Cookie)&&socketHealthy(){return};panic("partial running state; stop first")}
  // Bind preflight is deliberately fail-closed; never terminate an unrelated listener.
  ln,e:=net.Listen("tcp4","127.0.0.1:18080");must(e);ln.Close()
  rt:=filepath.Join(dest,"runtime");libs:=strings.Join([]string{rt+"/lib",rt+"/usr/lib",rt+"/usr/lib/libproxy"},":")
  env:=append(os.Environ(),"SSL_CERT_FILE="+rt+"/etc/ssl/cert.pem","HOME="+data,"QT_PLUGIN_PATH="+rt+"/usr/lib/qt6/plugins")
  s=State{};s.QB=launch([]string{rt+"/lib/ld-musl-x86_64.so.1","--library-path",libs,rt+"/usr/bin/qbittorrent-nox","--profile="+path("profile"),"--confirm-legal-notice"},env,"qb.log");save(s)
  ok:=false;defer func(){if !ok{stopOne(s.Gateway);stopOne(s.QB)}}()
  end:=time.Now().Add(25*time.Second);for time.Now().Before(end){if !owned(s.QB){panic("qB exited; inspect private qb.log")};s.Cookie=login();if s.Cookie!=""&&version(s.Cookie){break};time.Sleep(200*time.Millisecond)}
  if !version(s.Cookie){panic("qB health/login timeout; inspect private qb.log (do not publish temporary credentials)")}
  if read(path("backend-password"))==""{b:=make([]byte,32);_,e:=rand.Read(b);must(e);pw:=base64.RawURLEncoding.EncodeToString(b);j,_:=json.Marshal(map[string]string{"web_ui_username":"admin","web_ui_password":pw});req,_:=http.NewRequest("POST","http://127.0.0.1:18080/api/v2/app/setPreferences",strings.NewReader(url.Values{"json":{string(j)}}.Encode()));req.Header.Set("Cookie",s.Cookie);req.Header.Set("Content-Type","application/x-www-form-urlencoded");res,e:=client().Do(req);must(e);io.Copy(io.Discard,res.Body);res.Body.Close();if res.StatusCode!=200{panic("backend password initialization failed")};must(os.WriteFile(path("backend-password"),[]byte(pw),0600));s.Cookie=login();if !version(s.Cookie){panic("backend credential readback failed")}}
  save(s)
  env=append(os.Environ(),"BACKEND_COOKIE="+s.Cookie,"BACKEND_PASSWORD_FILE="+path("backend-password"),"BACKEND_URL=http://127.0.0.1:18080","GATEWAY_SOCKET="+filepath.Join(dest,"app.sock"))
  s.Gateway=launch([]string{filepath.Join(dest,"bin/gateway")},env,"gateway.log");save(s)
  end=time.Now().Add(10*time.Second);for time.Now().Before(end){if socketHealthy(){ok=true;return};time.Sleep(100*time.Millisecond)};panic("gateway health timeout")
 default:panic("unsupported lifecycle action")
 }
}
