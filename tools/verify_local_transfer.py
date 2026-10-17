import pathlib,subprocess,os,time,re,urllib.request,urllib.parse,http.cookiejar,json,uuid
r=pathlib.Path(__file__).resolve().parents[1];d=r/'.runtime/local-swarm';(d/'downloads').mkdir(parents=True,exist_ok=True);(d/'config/qBittorrent/config').mkdir(parents=True,exist_ok=True)
(d/'downloads/legal-test.txt').write_bytes((r/'.runtime/downloads/legal-test.txt').read_bytes());(d/'config/qBittorrent/config/qBittorrent.conf').write_text('[BitTorrent]\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\nSession\\Port=6881\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Port=18081\nWebUI\\HostHeaderValidation=true\nWebUI\\ServerDomains=localhost\n')
net='fnos-qbt-isolated-swarm';name='fnos-qbt-local-seed';subprocess.run(['docker','network','create','--internal',net],capture_output=True);subprocess.run(['docker','network','connect',net,'fnos-qbt-test'],capture_output=True)
def client(base,password):
 op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));op.open(base+'/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':password}).encode()).read();return op

def call(op,base,path,fields=None):
 data=None if fields is None else urllib.parse.urlencode(fields).encode();return op.open(base+'/api/v2/'+path,data,timeout=15).read()
def add(op,base,path):
 boundary=uuid.uuid4().hex;data=b''
 for key,value in [('savepath',path),('stopped','false')]:data+=f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
 data+=f'--{boundary}\r\nContent-Disposition: form-data; name="torrents"; filename="legal-test.torrent"\r\nContent-Type: application/x-bittorrent\r\n\r\n'.encode()+(r/'tests/fixtures/legal-test.torrent').read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
 op.open(urllib.request.Request(base+'/api/v2/torrents/add',data,{'Content-Type':'multipart/form-data; boundary='+boundary})).read()
try:
 subprocess.run(['docker','run','-d','--name',name,'--network',net,'--user',f'{os.getuid()}:{os.getgid()}','-e','QBT_LEGAL_NOTICE=confirm','-e','QBT_TORRENTING_PORT=6881','-v',str(d/'config')+':/config','-v',str(d/'downloads')+':/downloads','ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1'],check=True,capture_output=True)
 for _ in range(20):
  time.sleep(1);log=subprocess.check_output(['docker','logs',name],stderr=subprocess.STDOUT).decode();m=re.search(r'temporary password is provided for this session: (\S+)',log)
  if m:break
 else:raise RuntimeError('seed startup failure')
 ip=json.loads(subprocess.check_output(['docker','inspect',name]))[0]['NetworkSettings']['Networks'][net]['IPAddress'];seedbase=f'http://{ip}:18081';seed=client(seedbase,m[1]);call(seed,seedbase,'torrents/delete',{'hashes':'all','deleteFiles':'false'});time.sleep(.5);add(seed,seedbase,'/downloads')
 for _ in range(20):
  time.sleep(.5);s=json.loads(call(seed,seedbase,'torrents/info'))
  if s and s[0]['progress']==1:break
 else:raise RuntimeError('seed data hash check failed')
 base='http://127.0.0.1:18080';leecher=client(base,(r/'.runtime/password').read_text().strip());h=s[0]['hash'];call(leecher,base,'torrents/delete',{'hashes':h,'deleteFiles':'false'});time.sleep(.5);target=r/'.runtime/downloads/receive/legal-test.txt'
 if target.exists(): target.unlink()
 import shutil
 receive=r/'.runtime/downloads'/('receive-'+uuid.uuid4().hex);receive.mkdir()
 call(leecher,base,'app/setPreferences',{'json':json.dumps({'temp_path_enabled':False})})
 add(leecher,base,'/downloads/'+receive.name);time.sleep(1);call(leecher,base,'torrents/addPeers',{'hashes':h,'peers':f'{ip}:6881'})
 for _ in range(60):
  time.sleep(1);tasks=json.loads(call(leecher,base,'torrents/info'));t=next((t for t in tasks if t['hash']==h),None)
  if t and t['progress']==1 and t['downloaded']==74:break
 else:raise RuntimeError('local transfer did not complete')
 target=receive/'legal-test.txt';assert t['downloaded']==74;assert target.read_bytes()==(d/'downloads/legal-test.txt').read_bytes();result={'network':'internal Docker network; no tracker; DHT/PeX/LSD disabled','seed_version':call(seed,seedbase,'app/version').decode(),'leecher_version':call(leecher,base,'app/version').decode(),'payload_bytes':target.stat().st_size,'progress':t['progress'],'downloaded':t['downloaded'],'content_verified':True};(r/'evidence/local-transfer.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:
 subprocess.run(['docker','rm','-f',name],capture_output=True);subprocess.run(['docker','network','disconnect',net,'fnos-qbt-test'],capture_output=True);subprocess.run(['docker','network','rm',net],capture_output=True)
