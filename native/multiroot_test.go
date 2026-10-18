package main

import (
 "os"
 "path/filepath"
 "strings"
 "testing"
)

func TestPrepareThreeOfficialColonSeparatedShares(t *testing.T) {
 if os.Getuid()==0 { t.Skip("package-like nonroot UID required") }
 data=t.TempDir(); dest=t.TempDir()
 base:=t.TempDir()
 roots:=[]string{filepath.Join(base,"vol1","下载 空格"),filepath.Join(base,"vol2","电影"),filepath.Join(base,"vol3","备份")}
 for _,r:=range roots { if e:=os.MkdirAll(r,0700);e!=nil {t.Fatal(e)} }
 t.Setenv("TRIM_UID", "");t.Setenv("TRIM_DATA_SHARE_PATHS",strings.Join(roots,":"))
 prepare()
 conf:=path("profile/qBittorrent/config/qBittorrent.conf")
 if !strings.Contains(read(conf),"Session\\DefaultSavePath="+roots[0]+"\n") {t.Fatal("fresh install default is not first declared root")}
 // Only the default share is initialized: discovery must not write into other grants.
 for _,r:=range roots[1:] { if _,e:=os.Stat(filepath.Join(r,"incomplete"));!os.IsNotExist(e){t.Fatal("unexpected write to secondary root")} }
 before:=strings.Replace(read(conf),"Session\\DefaultSavePath="+roots[0],"Session\\DefaultSavePath="+roots[2],1)
 if e:=os.WriteFile(conf,[]byte(before),0600);e!=nil{t.Fatal(e)}
 t.Setenv("TRIM_DATA_SHARE_PATHS",strings.Join([]string{roots[1],roots[0],roots[2]},":"));prepare()
 if !strings.Contains(read(conf),"Session\\DefaultSavePath="+roots[2]+"\n") {t.Fatal("upgrade lost existing directory")}
}
