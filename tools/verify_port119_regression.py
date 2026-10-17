"""Isolated qB profile; never connects to NAS or existing task data."""
import pathlib,os,subprocess,time,re,urllib.request,urllib.parse,json,socket
R=pathlib.Path(__file__).resolve().parents[1];D=R/'.runtime/port119-regression';D.mkdir(exist_ok=True);pkg=os.environ.get('PORT_TEST_PACKAGE','.runtime/package119');rt=R/pkg/'app/runtime';C=D/'qBittorrent/config';C.mkdir(parents=True,exist_ok=True)
(C/'qBittorrent.conf').write_text('[BitTorrent]\nSession\\Port=49160\nSession\\UseRandomPort=false\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Address=127.0.0.1\nWebUI\\Port=18126\nWebUI\\HostHeaderValidation=true\nWebUI\\CSRFProtection=true\nWebUI\\ServerDomains=127.0.0.1\n')
def start():
 f=open(D/'private-process.log','w');os.chmod(D/'private-process.log',0o600)
 p=subprocess.Popen([str(rt/'lib/ld-musl-x86_64.so.1'),'--library-path',f'{rt}/lib:{rt}/usr/lib:{rt}/usr/lib/libproxy',str(rt/'usr/bin/qbittorrent-nox'),'--profile='+str(D),'--confirm-legal-notice'],stdout=f,stderr=f,env=dict(os.environ,QT_PLUGIN_PATH=str(rt/'usr/lib/qt6/plugins')))
 for _ in range(100):
  time.sleep(.1);m=re.search(r'session: (\S+)',(D/'private-process.log').read_text())
  if m:
   try:
    req=urllib.request.Request('http://127.0.0.1:18126/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':m[1]}).encode());cookie=urllib.request.urlopen(req).headers['Set-Cookie'].split(';')[0];return p,f,cookie
   except OSError:pass
 p.terminate();p.wait();raise RuntimeError('isolated readiness failure')
def prefs(cookie):return json.load(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18126/api/v2/app/preferences',headers={'Cookie':cookie})))
p,f,cookie=start()
try:
 subprocess.run(['node','tools/verify_port119_regression.mjs'],env=dict(os.environ,DIAGNOSTIC_TEST_COOKIE=cookie),cwd=R,check=True)
finally:p.terminate();p.wait(timeout=20);f.close()
p,f,cookie=start()
try:
 actual=prefs(cookie)
 for k,v in dict(listen_port=49160,random_port=False,dht=False,pex=False,lsd=False,upnp=False).items():assert actual[k]==v,(k,actual[k])
 s=socket.create_connection(('127.0.0.1',49160),timeout=2);s.close()
 (R/'evidence/port119-regression-persistence.json').write_text(json.dumps({'backend_restart_readback':{k:actual[k] for k in ['listen_port','random_port','dht','pex','lsd','upnp']},'tcp_listener_49160':True,'passed':True},indent=2));print('real backend restart persistence and TCP listener PASS')
finally:p.terminate();p.wait(timeout=20);f.close()
