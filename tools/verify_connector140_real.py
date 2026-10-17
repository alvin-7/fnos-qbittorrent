"""Isolated Docker client using MoviePilot's pinned qbittorrent-api dependency."""
from pathlib import Path
import os,subprocess,socket,http.client,json,time,uuid,urllib.parse,re,hashlib,secrets
R=Path(__file__).resolve().parents[1]
# Require an explicitly chosen local test interface; never default to a private host.
TEST_BIND=os.environ.get('CONNECTOR_TEST_BIND')
if not TEST_BIND:
 raise SystemExit('CONNECTOR_TEST_BIND is required for the isolated Docker regression')
source=(R/'tools/verify_pt119_real.py').read_text().split('\ntry:\n')[0].replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')').replace('.runtime/pt119','.runtime/connector140')
source=re.sub(r"\{\{SECRET_[^}]+\}\}\(\)","getattr(uuid,'uuid4')()",source).replace(".runtime/package119",".runtime/package140");exec(source)
D=D/('run-'+secrets.token_bytes().hex()[:8]);D.mkdir()
D.mkdir(exist_ok=True);(D/'gateway.sock').unlink(missing_ok=True); q=None;g=None;container='mp140-'+secrets.token_bytes().hex()[:8];network=container+'-net'; password=secrets.token_bytes().hex()+secrets.token_bytes().hex()
class Unix(http.client.HTTPConnection):
 def connect(self):self.sock=socket.socket(socket.AF_UNIX);self.sock.connect(str(D/'gateway.sock'))
def manage(path,fields=None):
 c=Unix('local',timeout=30);data=None if fields is None else urllib.parse.urlencode(fields);c.request('GET' if fields is None else 'POST','/app/fnos-qbittorrent-native/api/v2/connector/'+path,data,{'Origin':'http://local','X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':'fnos-gateway','Content-Type':'application/x-www-form-urlencoded'});r=c.getresponse();b=r.read();assert r.status==200,(r.status,b);return json.loads(b)
def run(*args):return subprocess.check_output(args,text=True).strip()
try:
 q=QB('backend',18080,16981)
 # Isolated temporary backend credential, never a real NAS credential.
 temp=re.search(r'session: (\S+)',(q.root/'private.log').read_text())[1]
 pw=D/'backend-password';pw.write_text(temp);pw.chmod(0o600)
 log=open(D/'gateway.log','w');g=subprocess.Popen(['docker','run','--rm','--name',container+'-gateway','--user',str(os.getuid())+':'+str(os.getgid()),'--network','host','-v',str(R)+':'+str(R),'-e','BACKEND_PASSWORD_FILE='+str(pw),'-e','BACKEND_URL=http://127.0.0.1:18080','-e','GATEWAY_SOCKET='+str(D/'gateway.sock'),'alpine:3.22',str(R/'.runtime/package140/app/bin/gateway')],stdout=log,stderr=log)
 for _ in range(100):
  if (D/'gateway.sock').exists():break
  time.sleep(.1)
 run('docker','network','create',network)
 net=json.loads(run('docker','network','inspect',network))[0];gateway=socket.gethostbyname_ex(socket.gethostname())[2][0]
 gateway=TEST_BIND # Caller-selected, verified local interface; never a product default.
 run('docker','run','-d','--name',container,'--network',network,'--add-host','host.docker.internal:'+gateway,'-v',str(D.resolve())+':/fixture:ro','python:3.11.13-slim-bookworm','sleep','600')
 addr=json.loads(run('docker','inspect',container))[0]['NetworkSettings']['Networks'][network]['IPAddress']
 config={'enabled':True,'bindIP':gateway,'port':18081,'username':'moviepilot-fixture','password':password,'allowedCIDRs':[addr+'/32'],'trustedHTTP':True}
 # Bootstrap marker is public, not a password: discover it using protected Unix transport.
 c=Unix('local');c.request('POST','/app/fnos-qbittorrent-native/gateway/session','',{'Origin':'http://local','X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-Bootstrap':'1'});r=c.getresponse();token=json.loads(r.read())['token'];c.close()
 oldmanage=manage
 def manage(path,fields=None):
  c=Unix('local',timeout=30);data=None if fields is None else urllib.parse.urlencode(fields);c.request('GET' if fields is None else 'POST','/app/fnos-qbittorrent-native/api/v2/connector/'+path,data,{'Origin':'http://local','X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':token,'Content-Type':'application/x-www-form-urlencoded'});r=c.getresponse();b=r.read();assert r.status==200,(r.status,b);return json.loads(b)
 assert not manage('status')['listening'];manage('configure',{'json':json.dumps(config)})
 secret=D/'client.json';secret.write_text(json.dumps({'username':config['username'],'password':password}));secret.chmod(0o600)
 subprocess.run(['docker','exec',container,'pip','install','--disable-pip-version-check','qbittorrent-api==2026.6.0'],check=True,stdout=subprocess.DEVNULL)
 client='''import qbittorrentapi,json,hashlib,time,requests
s=json.load(open('/fixture/client.json'))
c=qbittorrentapi.Client(host='http://host.docker.internal:18081',**s,REQUESTS_ARGS={'timeout':10})
c.auth_log_in();assert c.app.version=='v5.2.4';before=[t.hash for t in c.torrents_info()]
c.torrents_create_category(name='MP-fixture',save_path='');assert 'MP-fixture' in c.torrents_categories()
c.torrents_create_category(name='MP-empty',save_path='');assert 'MP-empty' in c.torrents_categories()
c.torrents_edit_category(name='MP-empty',save_path='/isolated-empty');assert c.torrents_categories()['MP-empty']['savePath']=='/isolated-empty'
c.torrents_remove_categories(categories='MP-empty');assert 'MP-empty' not in c.torrents_categories()
c.torrents_create_tags(tags='MP-tag');assert 'MP-tag' in c.torrents_tags()
def enc(v):
 if isinstance(v,int):return b'i'+str(v).encode()+b'e'
 if isinstance(v,bytes):return str(len(v)).encode()+b':'+v
 return b'd'+b''.join(enc(k)+enc(w) for k,w in sorted(v.items()))+b'e'
info={b'name':b'isolated-connector.bin',b'length':4,b'piece length':16384,b'pieces':hashlib.sha1(b'test').digest(),b'private':1};h=hashlib.sha1(enc(info)).hexdigest()
c.torrents_add(torrent_files=enc({b'info':info}),category='MP-fixture',tags='MP-tag',is_stopped=True)
for _ in range(40):
 tasks=c.torrents_info(torrent_hashes=h)
 if tasks:break
 time.sleep(.1)
assert len(tasks)==1 and tasks[0].category=='MP-fixture' and 'MP-tag' in tasks[0].tags
assert h not in before
c.torrents_add_tags(tags='second',torrent_hashes=h);assert 'second' in c.torrents_info(torrent_hashes=h)[0].tags
c.torrents_remove_tags(tags='second',torrent_hashes=h);assert 'second' not in c.torrents_info(torrent_hashes=h)[0].tags
c.torrents_delete_tags(tags='second');assert 'second' not in c.torrents_tags()
for path in ['management/config','diagnostics/socket','socket/file/path','file/read']:
 r=c._session.get('http://host.docker.internal:18081/api/v2/'+path); assert r.status_code in [403,404,405], (path,r.status_code,r.text[:200])
assert c._session.get('http://host.docker.internal:18081/api/v2/app/version',headers={'Origin':'http://evil.invalid'}).status_code==403
print(json.dumps({'client':'qbittorrent-api==2026.6.0','version':c.app.version,'hash_before':before,'hash_after':h,'category':'MP-fixture','tags':'MP-tag','multipart_add_confirmed':True,'tag_crud_readback':True,'malicious_origin_rejected':True,'sensitive_routes_rejected':True}))
'''
 script=D/'client.py';script.write_text(client)
 out=run('docker','exec',container,'python','/fixture/client.py');report=json.loads(out)
 assert q.task(report['hash_after'])
 status=manage('status');assert status['passwordSet'] and 'password' not in status
 assert oct((D/'moviepilot-private/connector.json').stat().st_mode&0o777)=='0o600'
 assert password not in (D/'gateway.log').read_text()
 config['enabled']=False;config['password']='';manage('configure',{'json':json.dumps(config)});assert not manage('status')['listening']
 report.update({'docker_source_allowlist':addr+'/32','actual_bind_interface':gateway,'host_alias_mapping_verified':True,'disable_listener_closed':True,'nas_verified':False,'full_acceptance':False})
 (R/'evidence/connector140-real.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if g:
  subprocess.run(['docker','rm','-f',container+'-gateway'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);g.wait(timeout=10)
 if q:q.stop()
 subprocess.run(['docker','rm','-f',container],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 subprocess.run(['docker','network','rm',network],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
