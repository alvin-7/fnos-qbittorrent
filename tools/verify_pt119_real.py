"""Two isolated native qB 5.2.4 fixtures; no NAS/config/clock changes."""
import pathlib,os,subprocess,time,re,urllib.request,urllib.parse,json,hashlib,uuid,datetime
R=pathlib.Path(__file__).resolve().parents[1];D=R/'.runtime/pt119';D.mkdir(exist_ok=True);rt=R/'.runtime/package119/app/runtime';report={'cases':[]};running=[]
def call(port,cookie,path,fields=None):
 data=None if fields is None else urllib.parse.urlencode(fields).encode()
 res=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{port}/api/v2/'+path,data,{'Cookie':cookie}),timeout=10)
 b=res.read().decode()
 try:return json.loads(b)
 except ValueError:return b
class QB:
 def __init__(self,name,port,bt):
  self.name=name;self.port=port;self.bt=bt;self.root=D/(name+'-'+uuid.uuid4().hex[:8]);self.root.mkdir(exist_ok=True);self.download=self.root/'downloads';self.download.mkdir(exist_ok=True);self.cookie=''
  conf=self.root/'qBittorrent/config';conf.mkdir(parents=True,exist_ok=True)
  if not (conf/'qBittorrent.conf').exists():(conf/'qBittorrent.conf').write_text(f'[BitTorrent]\nSession\\Port={bt}\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Address=127.0.0.1\nWebUI\\Port={port}\nWebUI\\HostHeaderValidation=true\nWebUI\\CSRFProtection=true\nWebUI\\ServerDomains=127.0.0.1\n')
  self.start()
 def start(self):
  log=self.root/'private.log';self.f=open(log,'w');os.chmod(log,0o600)
  self.p=subprocess.Popen([str(rt/'lib/ld-musl-x86_64.so.1'),'--library-path',f'{rt}/lib:{rt}/usr/lib:{rt}/usr/lib/libproxy',str(rt/'usr/bin/qbittorrent-nox'),'--profile='+str(self.root),'--confirm-legal-notice'],stdout=self.f,stderr=self.f,env=dict(os.environ,QT_PLUGIN_PATH=str(rt/'usr/lib/qt6/plugins'),TZ='UTC-8'))
  for _ in range(100):
   time.sleep(.1);m=re.search(r'session: (\S+)',log.read_text())
   if m:
    try:
     res=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.port}/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':m[1]}).encode()));self.cookie=res.headers['Set-Cookie'].split(';')[0]
     assert self.api('app/version')=='v5.2.4';return
    except OSError:pass
  raise RuntimeError('readiness failed '+self.name)
 def stop(self):
  self.p.terminate();self.p.wait(timeout=30);self.f.close()
 def api(self,path,fields=None):return call(self.port,self.cookie,path,fields)
 def prefs(self,**kw):
  if kw:self.api('app/setPreferences',{'json':json.dumps(kw)})
  p=self.api('app/preferences')
  for k,v in kw.items():assert p[k]==v,(k,p[k],v)
  return p
 def add(self,torrent):
  boundary=uuid.uuid4().hex;body=b''
  for k,v in [('savepath',str(self.download)),('stopped','false')]:body+=f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
  body+=f'--{boundary}\r\nContent-Disposition: form-data; name="torrents"; filename="fixture.torrent"\r\nContent-Type: application/x-bittorrent\r\n\r\n'.encode()+torrent+f'\r\n--{boundary}--\r\n'.encode()
  res=urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{self.port}/api/v2/torrents/add',body,{'Cookie':self.cookie,'Content-Type':'multipart/form-data; boundary='+boundary}));assert res.status in [200,202]
 def task(self,h):return next((t for t in self.api('torrents/info') if t['hash']==h),None)
def wait(fn,timeout=40):
 end=time.monotonic()+timeout
 while time.monotonic()<end:
  v=fn()
  if v:return v
  time.sleep(.2)
 raise AssertionError('bounded state timeout')
def enc(x):
 if isinstance(x,int):return b'i'+str(x).encode()+b'e'
 if isinstance(x,bytes):return str(len(x)).encode()+b':'+x
 if isinstance(x,dict):return b'd'+b''.join(enc(k)+enc(v) for k,v in sorted(x.items()))+b'e'
 raise TypeError(x)
def check(q,h,predicate):
 t=q.task(h);return t if t and predicate(t) else None
def brief(t):return {k:t.get(k) for k in ['state','progress','force_start','uploaded','downloaded','ratio','seeding_time','completed']}
try:
 a=QB('seed',18136,16936);running.append(a);b=QB('leecher',18137,16937);running.append(b)
 for q in [a,b]:q.prefs(dht=False,pex=False,lsd=False,upnp=False,queueing_enabled=False,dl_limit=0,up_limit=0,limit_lan_peers=True)
 payload=os.urandom(4*1024*1024);piece=256*1024;name=b'private-pt119.bin';info={b'length':len(payload),b'name':name,b'piece length':piece,b'pieces':b''.join(hashlib.sha1(payload[i:i+piece]).digest() for i in range(0,len(payload),piece)),b'private':1};torrent=enc({b'info':info});h=hashlib.sha1(enc(info)).hexdigest();(a.download/name.decode()).write_bytes(payload);a.add(torrent);wait(lambda:a.task(h) and a.task(h)['progress']==1);b.add(torrent);wait(lambda:b.task(h));b.api('torrents/addPeers',{'hashes':h,'peers':'127.0.0.1:16936'});wait(lambda:b.task(h)['progress']==1 and b.task(h)['downloaded']==len(payload),90)
 assert (b.download/name.decode()).read_bytes()==payload
 wait(lambda:a.task(h)['uploaded']>=len(payload))
 for q in [a,b]:
  assert q.api('torrents/properties?hash='+h)['private'] is True
  q.api('torrents/setForceStart',{'hashes':h,'value':'true'});t=wait(lambda:check(q,h,lambda t:t['state']=='forcedUP' and t['force_start']))
  report['cases'].append({'node':q.name,'force':brief(t)})
  q.api('torrents/stop',{'hashes':h});t=wait(lambda:check(q,h,lambda t:t['state']=='stoppedUP' and not t['force_start']));report['cases'].append({'node':q.name,'stop_after_force':brief(t)})
  q.api('torrents/setForceStart',{'hashes':h,'value':'false'});q.api('torrents/start',{'hashes':h});t=wait(lambda:check(q,h,lambda t:t['state'] in ['stalledUP','uploading','queuedUP'] and not t['force_start']));report['cases'].append({'node':q.name,'normal_start':brief(t)})
  p=q.api('torrents/properties?hash='+h);assert all(k in p for k in ['total_uploaded','share_ratio','seeding_time']);report[q.name+'_properties']={k:p[k] for k in ['total_uploaded','total_downloaded','share_ratio','seeding_time','private']}
 # Queue pressure: max_active_torrents=0 is valid but qB/libtorrent may treat zero; use a second seed blocker.
 a.prefs(queueing_enabled=True,max_active_uploads=0,max_active_torrents=1,dont_count_slow_torrents=False)
 a.api('torrents/setForceStart',{'hashes':h,'value':'false'});t=wait(lambda:check(a,h,lambda t:t['state']=='queuedUP'),35);report['queue']=brief(t)
 a.api('torrents/setForceStart',{'hashes':h,'value':'true'});wait(lambda:a.task(h)['state']=='forcedUP');report['force_bypasses_queue']=True
 a.prefs(queueing_enabled=False)
 values=dict(dl_limit=321*1024,up_limit=123*1024,alt_dl_limit=17*1024,alt_up_limit=19*1024,scheduler_enabled=False,schedule_from_hour=8,schedule_from_min=30,schedule_to_hour=20,schedule_to_min=15,scheduler_days=1)
 a.prefs(**values);a.stop();a.start();actual=a.prefs();assert all(actual[k]==v for k,v in values.items());report['restart_persistence']=values
 # Real near-time scheduler transitions; UTC+8 belongs to process only, not system clock.
 now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)));start=(now+datetime.timedelta(minutes=1)).replace(second=0,microsecond=0);end=start+datetime.timedelta(minutes=1)
 a.prefs(schedule_from_hour=start.hour,schedule_from_min=start.minute,schedule_to_hour=end.hour,schedule_to_min=end.minute,scheduler_days=0,scheduler_enabled=True)
 a.stop();a.start()
 wait(lambda:a.api('transfer/speedLimitsMode')==0,5);samples=[{'at':now.isoformat(),'mode':0}]
 wait(lambda:a.api('transfer/speedLimitsMode')==1,100);samples.append({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'mode':1,'limits':a.api('transfer/info')})
 assert samples[-1]['limits']['dl_rate_limit']==17*1024
 wait(lambda:a.api('transfer/speedLimitsMode')==0,100);samples.append({'at':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),'mode':0,'limits':a.api('transfer/info')});assert samples[-1]['limits']['up_rate_limit']==123*1024
 report['scheduler_real_trigger']={'process_TZ':'UTC-8 (fixed UTC+08:00)','browser_timezone_irrelevant':True,'start':start.isoformat(),'end':end.isoformat(),'samples':samples,'cross_midnight_trigger_tested':False}
 a.prefs(scheduler_enabled=False)
 # UI fixture uses completed leecher with nonzero true downloaded count; seed proves upload/ratio.
 b.prefs(save_path=str(b.download),temp_path=str(b.download/'incomplete'),alternative_webui_enabled=True,alternative_webui_path=str(R/'.runtime/package119/app/webui'))
 (R/'evidence/pt119-real-progress.json').write_text(json.dumps(report,indent=2))
 subprocess.run(['node','tools/verify_pt119_browser.mjs'],cwd=R,env=dict(os.environ,PT119_COOKIE=b.cookie,PT119_HASH=h),check=True)
 report['transfer']={'bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),'seed':brief(a.task(h)),'leecher':brief(b.task(h)),'private':True,'discovery_off':True};report['passed']=True
 (R/'evidence/pt119-real.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 for q in reversed(running):
  if q.p.poll() is None:q.stop()
