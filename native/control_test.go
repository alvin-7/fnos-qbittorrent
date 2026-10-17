package main
import("testing";"os";"path/filepath";"strings")
func TestPrepareEnforcesPrivateCustomUIOnExistingProfile(t *testing.T){
 if os.Getuid()==0{t.Skip("requires package user")};data=t.TempDir();dest=t.TempDir();share:=t.TempDir();t.Setenv("TRIM_DATA_SHARE_PATHS",share);t.Setenv("TRIM_UID","")
 conf:=filepath.Join(data,"profile/qBittorrent/config/qBittorrent.conf");os.MkdirAll(filepath.Dir(conf),0700)
 os.WriteFile(conf,[]byte("[Preferences]\nWebUI\\Address=*\nWebUI\\LocalHostAuth=false\nWebUI\\AlternativeUIEnabled=false\nWebUI\\AuthSubnetWhitelistEnabled=true\nWebUI\\RootFolder=/wrong\n[BitTorrent]\nSession\\DefaultSavePath=/preserve\n"),0600)
 prepare();got:=read(conf)
 for _,want:=range []string{"WebUI\\Address=127.0.0.1","WebUI\\LocalHostAuth=true","WebUI\\AlternativeUIEnabled=true","WebUI\\AuthSubnetWhitelistEnabled=false","WebUI\\RootFolder="+filepath.Join(dest,"webui"),"Session\\DefaultSavePath=/preserve"}{if !strings.Contains(got,want+"\n"){t.Errorf("missing %q",want)}}
}
