"""Current UI + real pinned qB + Unix gateway; no package, Git or NAS operations."""
from pathlib import Path
import os,subprocess,re,shutil,json
R=Path(__file__).resolve().parents[1]
s=(R/'tools/verify_workspace154_real.py').read_text()
s=s.replace(".runtime/workspace154-verification-",".runtime/status-current-")
s=s.replace(" q=QB('directory',18080,16988)"," q=QB('status-current',18080,16988)")
a=s.index(" q.prefs(");b=s.index(" private=D/'private'",a)
s=s[:a]+''' web=D/'webui'
 subprocess.run(['node','node_modules/vite/bin/vite.js','build','--base=./','--outDir',str(web/'public')],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
 for p in (web/'public').rglob('*.js'):p.write_text(p.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
 shutil.copytree(web/'public',web/'private')
 q.prefs(save_path=str(q.download),temp_path=str(q.download/'incomplete'),temp_path_enabled=False,alternative_webui_enabled=True,alternative_webui_path=str(web),dht=False,pex=False,lsd=False,upnp=False)
 q.api('torrents/createCategory',{'category':'Acceptance-category','savePath':''});q.api('torrents/createTags',{'tags':'Acceptance-tag'});q.api('torrents/setCategory',{'hashes':h,'category':'Acceptance-category'});q.api('torrents/addTags',{'hashes':h,'tags':'Acceptance-tag'})
 extra=hashlib.sha1(b'status-current-extra').hexdigest();q.api('torrents/add',{'urls':'magnet:?xt=urn:btih:'+extra,'savepath':str(q.download),'stopped':'true'});wait(lambda:len(q.api('torrents/info'))==2)
 assert q.api('app/version')=='v5.2.4'
'''+s[b:]
a=s.index(" subprocess.run(['node','tools/verify_workspace154_browser.mjs']");b=s.index('\nfinally:',a)
s=s[:a]+''' subprocess.run(['node','tools/verify_status_browser_current.mjs'],cwd=R,env=dict(os.environ,GATEWAY_SOCKET=str(sock)),check=True)
 print('PASS current-source real qB 5.2.4 Unix gateway')
'''+s[b:]
s=s.replace('import os,subprocess,time,uuid,re,json,http.server', 'import os,subprocess,time,uuid,re,json,shutil,http.server')
exec(compile(s,str(R/'tools/verify_workspace154_real.py'),'exec'))
