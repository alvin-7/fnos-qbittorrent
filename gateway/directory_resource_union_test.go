package main
import("context";"os";"path/filepath";"testing")
func TestDirectoryResourceShareUnion(t *testing.T){
 b:=t.TempDir();own:=filepath.Join(b,"app","downloads");a:=filepath.Join(b,"vol1","qBittorrent");c:=filepath.Join(b,"vol2","qBittorrent")
 for _,p:=range []string{own,a,c}{if e:=os.MkdirAll(p,0700);e!=nil{t.Fatal(e)}}
 t.Setenv("TRIM_DATA_SHARE_PATHS",own+":"+own);t.Setenv("TRIM_DATA_ACCESSIBLE_PATHS",filepath.Join(b,"never-authorized"))
 p:=&mockDirectoryProvider{paths:[]string{a,c}};s:=newDirectoryService(p);roots,_,e:=s.roots(context.Background(),"1000")
 if e!=nil||len(roots)!=3{t.Fatalf("resource share must union dynamic same-name roots without fallback: got=%d err=%v",len(roots),e)}
 ids:=map[string]bool{};for _,r:=range roots{if ids[r.RootID]{t.Fatal("ID collision")};ids[r.RootID]=true}
 p.denied=own;roots,_,e=s.roots(context.Background(),"1000");if e!=nil||len(roots)!=2{t.Fatal("own share must retain per-user ACL",e)}
 p.failed=true;if _,_,e=s.roots(context.Background(),"1000");e==nil{t.Fatal("resource union must not bypass provider failure")}
}
