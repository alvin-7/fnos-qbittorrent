import pathlib,subprocess,os,json,time,urllib.request,urllib.parse,http.cookiejar,re,uuid,hashlib
R=pathlib.Path(__file__).resolve().parents[1];D=R/'.runtime/native-test';A=R/'native-package/app';report={}
env=dict(os.environ,TRIM_APPDEST=str(A),TRIM_PKGVAR=str(D),TRIM_DATA_SHARE_PATHS=str(D/'downloads'))
def ctl(action):return subprocess.run([str(R/'native-package/cmd/main'),action],env=env,capture_output=True).returncode
def call(port,path,fields=None,cookie=None):
 h={} if cookie is None else {'Cookie':cookie};data=None if fields is None else urllib.parse.urlencode(fields).encode();res=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}/api/v2/'+path,data,h),timeout=5);return res.read()
cookie=json.loads((D/'state.json').read_text())['Cookie']
assert ctl('status')==0;report['version']=call(18080,'app/version',cookie=cookie).decode();assert report['version']=='v5.2.4'
try:call(18080,'app/version');raise AssertionError('unauth allowed')
except urllib.error.HTTPError as e:assert e.code==403;report['loopback_without_auth']=e.code
prefs=json.loads(call(18080,'app/preferences',cookie=cookie));assert all(not prefs[k] for k in ['dht','pex','lsd','upnp']);assert prefs['web_ui_csrf_protection_enabled'] and prefs['web_ui_host_header_validation_enabled'];report['pt_defaults']=True
call(18080,'app/setPreferences',{'json':json.dumps({'dl_limit':333824,'temp_path_enabled':False})},cookie);assert json.loads(call(18080,'app/preferences',cookie=cookie))['dl_limit']==333824;report['settings_readback']=True
# Real native second qB, private trackerless fixture, manual loopback peer.
seed=D/'seed';(seed/'qBittorrent/config').mkdir(parents=True,exist_ok=True);payload=(R/'.runtime/downloads/legal-test.txt').read_bytes();(seed/'legal-test.txt').write_bytes(payload)
(seed/'qBittorrent/config/qBittorrent.conf').write_text('[BitTorrent]\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\nSession\\Port=16882\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Address=127.0.0.1\nWebUI\\Port=18081\nWebUI\\HostHeaderValidation=true\nWebUI\\ServerDomains=127.0.0.1\n')
rt=A/'runtime';log=open(seed/'run.log','w');p=subprocess.Popen([str(rt/'lib/ld-musl-x86_64.so.1'),'--library-path',f'{rt}/lib:{rt}/usr/lib:{rt}/usr/lib/libproxy',str(rt/'usr/bin/qbittorrent-nox'),'--profile='+str(seed),'--confirm-legal-notice'],stdout=log,stderr=log,env=dict(os.environ,QT_PLUGIN_PATH=str(rt/'usr/lib/qt6/plugins')))
def add(port,cookie,save):
 boundary=uuid.uuid4().hex;body=b''
 for k,v in [('savepath',str(save)),('stopped','false')]:body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
 body+=f'--{boundary}\r\nContent-Disposition: form-data; name="torrents"; filename="legal.torrent"\r\nContent-Type: application/x-bittorrent\r\n\r\n'.encode()+(R/'tests/fixtures/legal-test.torrent').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
 res=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}/api/v2/torrents/add',body,{'Cookie':cookie,'Content-Type':'multipart/form-data; boundary='+boundary}));assert res.status in [200,202]
try:
 for _ in range(30):
  time.sleep(.2);m=re.search(r'session: (\S+)',(seed/'run.log').read_text())
  if m:break
 op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));res=op.open('http://127.0.0.1:18081/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':m[1]}).encode());sc=res.headers['Set-Cookie'].split(';')[0];assert call(18081,'app/version',cookie=sc)==b'v5.2.4'
 call(18081,'torrents/delete',{'hashes':'all','deleteFiles':'false'},sc);time.sleep(.3);add(18081,sc,seed)
 for _ in range(50):
  tasks=json.loads(call(18081,'torrents/info',cookie=sc))
  if tasks and tasks[0]['progress']==1:break
  time.sleep(.2)
 else:raise AssertionError('seed hash check failed')
 h=tasks[0]['hash'];call(18080,'torrents/delete',{'hashes':h,'deleteFiles':'false'},cookie);time.sleep(.3);receive=D/'downloads'/('receive-'+uuid.uuid4().hex);receive.mkdir();add(18080,cookie,receive)
 for _ in range(10):
  tasks=json.loads(call(18080,'torrents/info',cookie=cookie))
  if any(t['hash']==h for t in tasks):break
  time.sleep(.2)
 call(18080,'torrents/addPeers',{'hashes':h,'peers':'127.0.0.1:16882'},cookie)
 for _ in range(100):
  t=next(t for t in json.loads(call(18080,'torrents/info',cookie=cookie)) if t['hash']==h)
  if t['progress']==1 and t['downloaded']==len(payload):break
  time.sleep(.3)
 else:raise AssertionError('native transfer timeout '+str(t['state']))
 assert (receive/'legal-test.txt').read_bytes()==payload
 report['native_private_transfer']={'progress':t['progress'],'downloaded':t['downloaded'],'payload_sha256':hashlib.sha256(payload).hexdigest(),'seed_version':'v5.2.4','leecher_version':'v5.2.4','discovery':False}
finally:p.terminate();p.wait(timeout=15);log.close()
assert ctl('stop')==0;assert ctl('status')==3;assert ctl('start')==0;cookie=json.loads((D/'state.json').read_text())['Cookie'];assert ctl('status')==0;assert json.loads(call(18080,'app/preferences',cookie=cookie))['dl_limit']==333824;assert any(t['hash']==h for t in json.loads(call(18080,'torrents/info',cookie=cookie)));report['restart_persistence']=True
(R/'evidence/native-runtime.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
