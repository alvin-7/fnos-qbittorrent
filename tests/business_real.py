"""Isolated business acceptance; no NAS, user URLs, or existing qB instances."""
import pathlib,subprocess,os,time,re,urllib.request,urllib.parse,http.cookiejar,json,uuid,threading,http.server,hashlib
root=pathlib.Path(__file__).resolve().parents[1]
suffix=uuid.uuid4().hex[:8];directory=pathlib.Path(os.environ['TMPDIR'])/('qbt-business-'+suffix);directory.mkdir()
net='qbt-business-'+suffix;names=['qbt-biz-seed-'+suffix,'qbt-biz-download-'+suffix];image='ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1'
def run(*args):return subprocess.check_output(args,stderr=subprocess.STDOUT).decode().strip()
def client(base,password):
 op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));op.open(base+'/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':password}).encode()).read();return op

def call(op,base,path,fields=None):return op.open(base+'/api/v2/'+path,None if fields is None else urllib.parse.urlencode(fields).encode(),timeout=10).read()
def add(op,base):
 boundary=uuid.uuid4().hex;data=b''
 for key,value in [('savepath','/downloads'),('stopped','false')]:data+=f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
 data+=f'--{boundary}\r\nContent-Disposition: form-data; name="torrents"; filename="fixture.torrent"\r\nContent-Type: application/x-bittorrent\r\n\r\n'.encode()+(root/'tests/fixtures/legal-test.torrent').read_bytes()+f'\r\n--{boundary}--\r\n'.encode();op.open(urllib.request.Request(base+'/api/v2/torrents/add',data,{'Content-Type':'multipart/form-data; boundary='+boundary})).read()
try:
 run('docker','network','create','--internal',net)
 contexts=[]
 for index,name in enumerate(names):
  d=directory/name;(d/'config/qBittorrent/config').mkdir(parents=True);(d/'downloads').mkdir();
  if index==0:(d/'downloads/legal-test.txt').write_bytes((root/'.runtime/downloads/legal-test.txt').read_bytes())
  (d/'config/qBittorrent/config/qBittorrent.conf').write_text('[BitTorrent]\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\nSession\\Port=6881\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Port=8080\nWebUI\\HostHeaderValidation=true\nWebUI\\ServerDomains=localhost\nWebUI\\CSRFProtection=true\n')
  run('docker','run','-d','--name',name,'--network',net,'--user',f'{os.getuid()}:{os.getgid()}','-e','QBT_LEGAL_NOTICE=confirm','-e','QBT_WEBUI_PORT=8080','-e','QBT_TORRENTING_PORT=6881','-v',str(d/'config')+':/config','-v',str(d/'downloads')+':/downloads',image)
  for _ in range(40):
   time.sleep(.5);logs=run('docker','logs',name);m=re.search(r'temporary password is provided for this session: (\S+)',logs)
   if m:break
  else:raise RuntimeError('qB did not initialize')
  ip=json.loads(run('docker','inspect',name))[0]['NetworkSettings']['Networks'][net]['IPAddress'];base='http://'+ip+':8080';op=client(base,m[1]);contexts.append((op,base,ip,m[1],d))
 seed,base,ip,_,seed_dir=contexts[0];add(seed,base)
 # Serve the controlled query endpoint inside the seed container: an internal
 # Docker network may deny container-to-host gateway connections.
 (seed_dir/'downloads/rss').write_bytes((root/'tests/fixtures/legal-test.torrent').read_bytes())
 subprocess.run(['go','build','-o',str(seed_dir/'downloads/fixture-http'),str(root/'tests/fixture-http.go')],env={**os.environ,'CGO_ENABLED':'0'},check=True)
 run('docker','exec','-d',names[0],'/downloads/fixture-http','/downloads/rss')
 for _ in range(40):
  tasks=json.loads(call(seed,base,'torrents/info'))
  if tasks and tasks[0]['progress']==1:break
  time.sleep(.5)
 else:raise RuntimeError('seed did not verify fixture')
 op,base,_,password,d=contexts[1]
 config=directory/'config.json';config.write_text(json.dumps({'base':base,'password':password,'hash':tasks[0]['hash'],'peer':ip+':6881','url':f'http://{ip}:8090/rss?id=fixture&sign=LOCAL_TEST_ONLY'}));config.chmod(0o600)
 subprocess.run(['node','tests/business-real.mjs',str(config)],cwd=root,check=True,timeout=180)
 target=d/'downloads/url/legal-test.txt';assert target.read_bytes()==(root/'.runtime/downloads/legal-test.txt').read_bytes()
 result=json.loads((root/'evidence/business-real.json').read_text());result.update(content_verified=True,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),network_internal=json.loads(run('docker','network','inspect',net))[0]['Internal'],image_id=run('docker','image','inspect',image,'--format','{{.Id}}'),seed_version=call(seed,contexts[0][1],'app/version').decode());(root/'evidence/business-real.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
 for name in names:subprocess.run(['docker','rm','-f',name],capture_output=True)
 subprocess.run(['docker','network','rm',net],capture_output=True)
 (directory/'config.json').unlink(missing_ok=True)
