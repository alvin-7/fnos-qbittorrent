package main
import("testing";"os";"path/filepath";"strings")
func TestPTPortFreshAndUpgrade(t *testing.T){
 if os.Getuid()==0{t.Skip("package user required")};data=t.TempDir();dest=t.TempDir();t.Setenv("TRIM_DATA_SHARE_PATHS",t.TempDir());t.Setenv("TRIM_UID","")
 prepare();conf:=filepath.Join(data,"profile/qBittorrent/config/qBittorrent.conf");got:=read(conf)
 for _,want:=range []string{"Session\\Port=49160","Session\\UseRandomPort=false","Session\\DHTEnabled=false","Session\\PeXEnabled=false","Session\\LSDEnabled=false","PortForwardingEnabled=false"}{if !strings.Contains(got,want+"\n"){t.Errorf("missing %s",want)}}
 got=strings.Replace(got,"Session\\Port=49160","Session\\Port=6881",1);os.WriteFile(conf,[]byte(got),0600);prepare();if !strings.Contains(read(conf),"Session\\Port=6881\n"){t.Fatal("upgrade changed user port")}
}
