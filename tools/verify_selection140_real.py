"""Isolated final package fixture only: no NAS, inherited tasks, or real credentials."""
from pathlib import Path
import os,subprocess,time,uuid,re,json,hashlib
R=Path(__file__).resolve().parents[1]
version=os.environ.get('SELECTION_PACKAGE','139')
s=(R/'tools/verify_pt119_real.py').read_text().split('\ntry:\n')[0].replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')').replace('.runtime/pt119','.runtime/selection140')
s=re.sub(r'\{\{SECRET_[^}]+\}\}\(\)', "getattr(uuid,'uuid4')()",s).replace("rt=R/'.runtime/package119/app/runtime'", "rt=R/'.runtime/package"+version+"/app/runtime'")
exec(s)
D=D/('run-'+getattr(uuid,'uuid4')().hex[:8]);D.mkdir();q=None;g=None
try:
 q=QB('ui',18080,16987)
 q.prefs(save_path=str(q.download),temp_path=str(q.download/'incomplete'),alternative_webui_enabled=True,alternative_webui_path=str(R/('.runtime/package'+version+'/app/webui')),queueing_enabled=False,dht=False,pex=False,lsd=False,upnp=False)
 for n in range(3):
  name=('selection-fixture-'+str(n)+'.bin').encode();data=b'test';(q.download/name.decode()).write_bytes(data);info={b'name':name,b'length':4,b'piece length':16384,b'pieces':hashlib.sha1(data).digest(),b'private':1};q.add(enc({b'info':info}))
 wait(lambda:len(q.api('torrents/info'))==3 and all(t['progress']==1 for t in q.api('torrents/info')))
 q.api('torrents/createCategory',{'category':'Selection category','savePath':''});q.api('torrents/createTags',{'tags':'Selection tag'})
 password=re.search(r'session: (\S+)',(q.root/'private.log').read_text())[1];pw=D/'backend-password';pw.write_text(password);pw.chmod(0o600);sock=D/'gateway.sock';log=open(D/'gateway.log','w')
 g=subprocess.Popen([str(R/('.runtime/package'+version+'/app/bin/gateway'))],env=dict(os.environ,BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock)),stdout=log,stderr=log)
 for _ in range(100):
  if sock.exists():break
  time.sleep(.1)
 assert sock.exists(),'gateway not ready'
 print('PASS isolated qB 5.2.4 + packaged Unix gateway ready, 3 private complete fixtures',flush=True)
 subprocess.run(['node','tools/verify_selection140_browser.mjs'],env=dict(os.environ,GATEWAY_SOCKET=str(sock)),cwd=R,check=True)
 state=q.api('torrents/info');(R/'evidence/selection140-real-readback.json').write_text(json.dumps({'backend':q.api('app/version'),'package':version,'tasks':[{k:t[k] for k in ['hash','name','state','force_start','category','tags','progress']} for t in state]},indent=2))
finally:
 if g:g.terminate();g.wait(timeout=10)
 if q:q.stop()
