"""Final UI + real isolated qB + test-only official fnOS HTTP contract socket."""
from pathlib import Path
import os,subprocess,time,uuid,re,json,http.server,socketserver,threading,http.client,socket,urllib.parse,hashlib
R=Path(__file__).resolve().parents[1];D=R/('.runtime/directory153-verification-'+getattr(uuid,'uuid4')().hex[:8]);D.mkdir()
s=(R/'tools/verify_pt119_real.py').read_text().split('\ntry:\n')[0].replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')').replace('.runtime/pt119','.runtime/directory153-qb')
s=re.sub(r'\{\{SECRET_[^}]+\}\}\(\)',"getattr(uuid,'uuid4')()",s).replace("rt=R/'.runtime/package119/app/runtime'","rt=R/'.runtime/package153/app/runtime'")
saved=D;exec(s);D=saved
q=g=platform=None
try:
 q=QB('directory',18080,16988)
 roots=[q.download,D/'vol2/qBittorrent',D/'vol3/qBittorrent',D/'vol2/个人 空格/xx']
 for root in roots:
  (root/'电影 🎬').mkdir(parents=True);(root/'incomplete').mkdir()
 mode=D/'mode';mode.write_text('ok');rootfile=D/'roots.json';rootfile.write_text(json.dumps(list(map(str,roots))));platform_socket=D/'platform.sock'
 class Platform(http.server.BaseHTTPRequestHandler):
  def log_message(self,*args):pass
  def do_POST(self):
   req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
   assert self.path=='/api/v1/trimapp' and req['appName']=='fnos-qbittorrent-native'
   stage='shared_grants' if req['req']=='trim.file.getSharedAccessibleFolders' else 'user_acl'
   if mode.read_text()==stage:result={'code':200003,'msg':'/secret/raw-platform-secret'}
   elif stage=='shared_grants':result={'code':0,'data':{'paths':list(map(str,roots))}}
   else:
    assert req['req']=='trim.file.checkUserACL' and req['data']['uid']==1000
    result={'code':0,'data':[{'path':p,'readable':True,'writable':True} for p in req['data']['path']]}
   self.send_response(200);self.end_headers();self.wfile.write(json.dumps(result).encode())
 platform=socketserver.UnixStreamServer(str(platform_socket),Platform);threading.Thread(target=platform.serve_forever,daemon=True).start()
 q.prefs(save_path=str(q.download),temp_path=str(q.download/'incomplete'),temp_path_enabled=False,alternative_webui_enabled=True,alternative_webui_path=str(R/'.runtime/package153/app/webui'),dht=False,pex=False,lsd=False,upnp=False)
 private=D/'private';private.mkdir();pw=private/'password';pw.write_text(re.search(r'session: (\S+)',(q.root/'private.log').read_text())[1]);pw.chmod(0o600);sock=D/'gateway.sock'
 sources=D/'gateway';sources.mkdir()
 for p in (R/'gateway').glob('*.go'):(sources/p.name).write_text(p.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
 binary=D/'test-gateway';subprocess.run(['go','test','-c','-o',str(binary),'.'],cwd=sources,env=dict(os.environ,GO111MODULE='off'),check=True)
 log=open(D/'gateway.log','w');g=subprocess.Popen([str(binary),'-test.run=TestDirectory153Server'],env=dict(os.environ,TRIM_API_TOKEN='test-only-fixture',DIRECTORY153_ROOTS=str(rootfile),DIRECTORY153_PLATFORM_SOCKET=str(platform_socket),BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock)),stdout=log,stderr=log);wait(lambda:sock.exists(),10)
 marker=re.search(r'r.Header.Get\(csrfHeader\) != "([^"]+)"',(R/'gateway/gateway_native.go').read_text())[1]
 subprocess.run(['node','tools/verify_directory153_browser.mjs'],cwd=R,env=dict(os.environ,GATEWAY_SOCKET=str(sock),DOWNLOAD_ROOT=str(q.download),PLATFORM_MODE=str(mode),CSRF_MARKER=marker),check=True)
 class Unix(http.client.HTTPConnection):
  def connect(self):self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.connect(str(sock))
 def request(route,fields,api=True):
  c=Unix('localhost');body=urllib.parse.urlencode(fields) if api else json.dumps(fields)
  c.request('POST','/app/fnos-qbittorrent-native/'+('api/v2/' if api else 'gateway/directories/')+route,body=body,headers={'X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':marker,'Origin':'http://localhost','Content-Type':'application/x-www-form-urlencoded' if api else 'application/json'});res=c.getresponse();data=res.read();c.close();return res.status,data
 status,b=request('roots',{},False);assert status==200 and len(json.loads(b)['roots'])==4
 for i,root in enumerate(roots):
  target=str(root/'电影 🎬');status,b=request('app/setPreferences',{'json':json.dumps({'save_path':target})});assert status==200,(status,b);assert q.api('app/preferences')['save_path']==target
 for i,root in enumerate(roots):
  target=str(root/'电影 🎬')
  h=hashlib.sha1(('isolated-directory153-'+str(i)).encode()).hexdigest();status,b=request('torrents/add',{'urls':'magnet:?xt=urn:btih:'+h,'savepath':target,'stopped':'true'});assert status in [200,202]
  task=wait(lambda:next((t for t in q.api('torrents/info') if t['hash']==h),None));assert task['save_path'].rstrip('/')==target
 before=len(q.api('torrents/info'));mode.write_text('user_acl');status,b=request('torrents/add',{'urls':'magnet:?xt=urn:btih:'+'a'*40,'savepath':str(roots[0]),'stopped':'true'});assert status==503 and json.loads(b)['code']=='AUTH_SCOPE_DENIED';assert len(q.api('torrents/info'))==before;mode.write_text('ok')
 g.terminate();g.wait();sock.unlink(missing_ok=True)
 g=subprocess.Popen([str(R/'.runtime/package153/app/bin/gateway')],env=dict(os.environ,TRIM_API_TOKEN='',BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock)),stdout=log,stderr=log);wait(lambda:sock.exists(),10)
 status,b=request('roots',{},False);assert status==503 and json.loads(b)['code']=='AUTH_TOKEN_MISSING'
 report={'status':'PASS','real_qb':'5.2.4','roots':4,'preferences_and_stopped_task_readbacks':4,'platform_200003_stages':['shared_grants','user_acl'],'blocked_mutation_zero_new_tasks':True,'final_packaged_gateway_missing_token':True,'provider':'test-only simulated official fnOS socket','NAS_verified':False,'uid':os.getuid()}
 (R/'evidence/directory153-real.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:
 if g:g.terminate();g.wait(timeout=10)
 if q:q.stop()
 if platform:platform.shutdown();platform.server_close()
