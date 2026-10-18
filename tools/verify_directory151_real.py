"""Isolated real qB + Go test-only fnOS provider; never a NAS acceptance."""
from pathlib import Path
import os,subprocess,time,uuid,re,json,hashlib
R=Path(__file__).resolve().parents[1];D=R/('.runtime/directory151-verification-'+getattr(uuid,'uuid4')().hex[:6]);D.mkdir(exist_ok=False)
s=(R/'tools/verify_pt119_real.py').read_text().split('\ntry:\n')[0].replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')').replace('.runtime/pt119','.runtime/directory151-qb')
s=re.sub(r'\{\{SECRET_[^}]+\}\}\(\)',"getattr(uuid,'uuid4')()",s).replace("rt=R/'.runtime/package119/app/runtime'","rt=R/'.runtime/package151/app/runtime'")
saved_verification=D
exec(s)
D=saved_verification
q=None;g=None
try:
 q=QB('directory',18080,16988);(q.download/'电影 🎬').mkdir();(q.download/'incomplete').mkdir();(q.download.parent/'not-authorized-secret').mkdir();(q.download/'not-a-directory.txt').write_text('file')
 q.prefs(save_path=str(q.download),temp_path=str(q.download/'incomplete'),temp_path_enabled=False,alternative_webui_enabled=True,alternative_webui_path=str(R/'.runtime/package151/app/webui'),dht=False,pex=False,lsd=False,upnp=False)
 (D/'private').mkdir();pw=D/'private/password';pw.write_text(re.search(r'session: (\S+)',(q.root/'private.log').read_text())[1]);pw.chmod(0o600);roots=D/'roots.json';roots.write_text(json.dumps([str(q.download)]));sock=D/'gateway.sock'
 sources=D/'gateway';sources.mkdir()
 for p in (R/'gateway').glob('*.go'):(sources/p.name).write_text(p.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
 binary=D/'test-gateway';subprocess.run(['go','test','-c','-o',str(binary),'.'],cwd=sources,env=dict(os.environ,GO111MODULE='off'),check=True)
 log=open(D/'test-gateway.log','w');g=subprocess.Popen([str(binary),'-test.run=TestDirectoryBrowserServer'],env=dict(os.environ,BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock),DIRECTORY_TEST_ROOT_FILE=str(roots)),stdout=log,stderr=log)
 wait(lambda:sock.exists(),10)
 subprocess.run(['node','tools/verify_directory151_browser.mjs'],env=dict(os.environ,GATEWAY_SOCKET=str(sock),DOWNLOAD_ROOT=str(q.download)),cwd=R,check=True)
 # Real save/read-back and task path under the test-only simulated provider.
 import http.client,socket
 class TestUnix(http.client.HTTPConnection):
  def connect(self):self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.connect(str(sock))
 marker=re.search(r'r.Header.Get\(csrfHeader\) != "([^"]+)"',(R/'gateway/gateway_native.go').read_text())[1]
 def protected(route,fields):
  c=TestUnix('localhost');c.request('POST','/app/fnos-qbittorrent-native/api/v2/'+route,body=urllib.parse.urlencode(fields),headers={'X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':marker,'Origin':'http://localhost','Content-Type':'application/x-www-form-urlencoded'});res=c.getresponse();data=res.read();c.close();return res.status,data
 target=str(q.download/'电影 🎬')
 status,data=protected('app/setPreferences',{'json':json.dumps({'save_path':target})});assert status==200,(status,data);assert q.api('app/preferences')['save_path']==target
 status,data=protected('torrents/add',{'urls':'magnet:?xt=urn:btih:6c3d4e5f67890123456789012345678901234567','savepath':target,'stopped':'true'});assert status in [200,202],(status,data)
 task=wait(lambda:next(iter(q.api('torrents/info')),None));assert task['save_path'].rstrip('/')==target
 (R/'evidence/directory151-real-readback.json').write_text(json.dumps({'provider':'SIMULATED fnOS, real local filesystem and qB 5.2.4','uid':os.getuid(),'preferences_save_path':q.api('app/preferences')['save_path'],'task':{k:task[k] for k in ['hash','state','save_path']},'NAS_package_UID_verified':False},indent=2))
 # Exercise final packaged gateway's missing-source behavior separately.
 g.terminate();g.wait();sock.unlink(missing_ok=True)
 g=subprocess.Popen([str(R/'.runtime/package151/app/bin/gateway')],env=dict(os.environ,TRIM_API_TOKEN='',BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock)),stdout=log,stderr=log);wait(lambda:sock.exists(),10)
 import http.client,socket
 class Unix(http.client.HTTPConnection):
  def connect(self):self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.connect(str(sock))
 marker=re.search(r'r.Header.Get\(csrfHeader\) != "([^"]+)"',(R/'gateway/gateway_native.go').read_text())[1]
 c=Unix('localhost');c.request('POST','/app/fnos-qbittorrent-native/gateway/directories/roots',body='{}',headers={'X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':marker,'Origin':'http://localhost','Content-Type':'application/json'});res=c.getresponse();assert res.status==503;assert json.loads(res.read())['code']=='AUTH_SOURCE_UNAVAILABLE';c.close()
 print('PASS final packaged gateway missing dynamic fnOS source fails closed; local provider remains explicitly simulated')
finally:
 if g:g.terminate();g.wait(timeout=10)
 if q:q.stop()
