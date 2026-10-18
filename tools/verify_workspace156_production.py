"""Additive final-FPK acceptance; run under unshare -Urnm with private /run and lo."""
from pathlib import Path
import os, tarfile, io, hashlib, json, subprocess
R=Path(__file__).resolve().parents[1]
O=R/'.runtime/workspace156-production'
O.mkdir(exist_ok=True)
fpk=R/'release/fnos-qbittorrent-native-1.5.6-x86_64.fpk'
with tarfile.open(fpk) as t:
 with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read()),mode='r:gz') as a:
  a.extractall(O/'package',filter='data')
package=O/'package'
assert (package/'bin/gateway').exists()
assert hashlib.sha256((package/'bin/gateway').read_bytes()).digest()==hashlib.sha256((R/'.runtime/package156/app/bin/gateway').read_bytes()).digest()
s=(R/'tools/verify_workspace154_real.py').read_text()
s=s.replace("R=Path(__file__).resolve().parents[1]",'R=Path('+repr(str(R))+')')
s=s.replace("platform_socket=D/'platform.sock'","platform_socket=Path('/var/run/trim_open_gateway_apiscope.socket')")
a=s.index(" sources=D/'gateway'");b=s.index(" marker=re.search",a)
s=s[:a]+''' binary=Path('''+repr(str(package/'bin/gateway'))+''')
 log=open(D/'gateway.log','w')
 def start_gateway(token='test-only-fixture'):
  sock.unlink(missing_ok=True)
  p=subprocess.Popen([str(binary)],env=dict(os.environ,TRIM_API_TOKEN=token,BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock)),stdout=log,stderr=log)
  wait(lambda:sock.exists(),10)
  return p
 g=start_gateway()
'''+s[b:]
s=s.replace("str(R/'.runtime/package154/app/webui')",repr(str(package/'webui')))
s=s.replace("g=subprocess.Popen([str(R/'.runtime/package156/app/bin/gateway')],env=dict(os.environ,TRIM_API_TOKEN='',BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:18080',GATEWAY_SOCKET=str(sock)),stdout=log,stderr=log);wait(lambda:sock.exists(),10)","g=start_gateway('')")
s=s.replace("tools/verify_workspace154_browser.mjs","tools/verify_workspace156_browser.mjs")
s=s.replace(".runtime/package154/app/runtime",str(package/'runtime'))
s=s.replace("str(R/'.runtime/package154/app/bin/gateway')",repr(str(package/'bin/gateway')))
s=s.replace(".runtime/package156/app/bin/gateway",str(package/'bin/gateway'))
point=" status,b=request('roots',{},False);assert status==200 and len(json.loads(b)['roots'])==4"
extra='''
 q.api('torrents/createCategory',{'category':'Acceptance-category','savePath':''});q.api('torrents/createTags',{'tags':'Acceptance-tag'});q.api('torrents/setCategory',{'hashes':h,'category':'Acceptance-category'});q.api('torrents/addTags',{'hashes':h,'tags':'Acceptance-tag'})
 extra_hashes=[]
 for i in range(25):
  eh=hashlib.sha1(('scroll-fixture-'+str(i)).encode()).hexdigest();extra_hashes.append(eh);q.api('torrents/add',{'urls':'magnet:?xt=urn:btih:'+eh,'savepath':str(q.download),'stopped':'true'})
 wait(lambda:len(q.api('torrents/info'))==26)
 subprocess.run(['node','tools/verify_workspace156_contracts.mjs'],cwd=R,env=dict(os.environ,GATEWAY_SOCKET=str(sock)),check=True)
 q.api('torrents/delete',{'hashes':'|'.join(extra_hashes),'deleteFiles':'false'});wait(lambda:len(q.api('torrents/info'))==1)
 status,b=request('storage',{},False);assert status==200
 volumes=json.loads(b)['volumes'];assert len(volumes)==1 and len(volumes[0]['roots'])==4
 v=volumes[0];st=os.statvfs(roots[0]);assert v['totalBytes']==st.f_blocks*st.f_frsize and v['usedBytes']==v['totalBytes']-v['freeBytes']
 g.terminate();g.wait();g=start_gateway()
 c=Unix('localhost');c.request('GET','/app/fnos-qbittorrent-native/api/v2/gateway/analysis/sites',headers={'X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':marker,'Origin':'http://localhost'});res=c.getresponse();site=json.loads(res.read());assert res.status==200 and site['eligibleHashes']==[h] and site['runningHashes']==[];c.close()
 for stage in ['shared_grants','user_acl']:
  mode.write_text(stage);status,b=request('roots',{},False);assert status==503 and json.loads(b)['code']=='AUTH_SCOPE_DENIED' and b'secret' not in b
 mode.write_text('ok')
 # Real connector session, credential rotation, restart persistence and disabled restart.
 def mg(route,config=None):
  status,data=request('connector/'+route,{} if config is None else {'json':json.dumps(config)}) if config is not None else (None,None)
  if config is None:
   c=Unix('localhost');c.request('GET','/app/fnos-qbittorrent-native/api/v2/connector/'+route,headers={'X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':marker,'Origin':'http://localhost'});r=c.getresponse();status,data=r.status,r.read();c.close()
  assert status==200,(route,status);return json.loads(data)
 secret=uuid.uuid4().hex+uuid.uuid4().hex
 cfg={'enabled':True,'bindIP':'127.0.0.1','port':18081,'username':'fixture','password':secret,'allowedCIDRs':['127.0.0.1/32'],'trustedHTTP':True}
 def client(route,fields=None,cookie=''):
  c=http.client.HTTPConnection('127.0.0.1',18081,timeout=5);body=None if fields is None else urllib.parse.urlencode(fields)
  c.request('GET' if fields is None else 'POST','/api/v2/'+route,body,{'Content-Type':'application/x-www-form-urlencoded','Cookie':cookie});r=c.getresponse();result=(r.status,r.read(),r.getheader('Set-Cookie','').split(';')[0]);c.close();return result
 mg('configure',cfg);assert mg('status')['listening'], 'initial connector listener'
 assert client('auth/login',{'username':'fixture','password':'wrong'})[0]==403
 code,_,cookie=client('auth/login',{'username':'fixture','password':secret});assert code in [200,204] and cookie
 assert client('app/version',cookie=cookie)[:2]==(200,b'v5.2.4')
 cfg['password']=uuid.uuid4().hex+uuid.uuid4().hex;mg('configure',cfg);assert client('app/version',cookie=cookie)[0]==403
 code,_,cookie=client('auth/login',{'username':'fixture','password':cfg['password']});assert code in [200,204]
 g.terminate();g.wait();g=start_gateway();assert mg('status')['listening'];assert client('app/version',cookie=cookie)[0]==403
 code,_,cookie=client('auth/login',{'username':'fixture','password':cfg['password']});assert code in [200,204] and client('app/version',cookie=cookie)[0]==200
 cfg['enabled']=False;cfg['password']='';mg('configure',cfg);assert not mg('status')['listening']
 g.terminate();g.wait();g=start_gateway();assert not mg('status')['listening']
 try:
  socket.create_connection(('127.0.0.1',18081),timeout=.5);raise AssertionError('disabled connector still open')
 except OSError:pass
'''
s=s.replace(point,point+extra)
# Mount fixtures after root creation, before provider/gateway startup.
mount_fixture="""
 mounts=[]
 for root in roots[:2]:
  target=root/'nested tmpfs';target.mkdir();subprocess.run(['mount','-t','tmpfs','-o','size=8m','tmpfs',str(target)],check=True);mounts.append(target)
  (target/'跨卷 子目录').mkdir()
  bind=root/'nested bind';bind.mkdir();subprocess.run(['mount','--bind',str(target),str(bind)],check=True);mounts.append(bind)
  for i in range(85):(root/('zz-scroll-%03d'%i)).mkdir()
  (root/'电影 🎬'/'深层 空格').mkdir()
  (root/'escape-link').symlink_to('/etc',target_is_directory=True)
"""
s=s.replace(" mode=D/'mode'",mount_fixture+" mode=D/'mode'")
s=s.replace(" class Unix(http.client.HTTPConnection):", " subprocess.run(['node','tools/verify_directory156_browser.mjs'],cwd=R,env=dict(os.environ,GATEWAY_SOCKET=str(sock),DOWNLOAD_ROOT=str(q.download),PLATFORM_MODE=str(mode),CSRF_MARKER=marker),check=True)\n class Unix(http.client.HTTPConnection):")
s=s.replace(" if platform:platform.shutdown();platform.server_close()", " if platform:platform.shutdown();platform.server_close()\n for mount in reversed(locals().get('mounts',[])):subprocess.run(['umount',str(mount)],check=True)")

s=s.replace("'provider':'test-only simulated official fnOS socket'","'provider':'FINAL FPK production binary + isolated namespace official Unix API socket', 'real_statfs_dedup':True,'private_aggregation':True,'connector_rotation_restart_disabled_restart':True")
s=s.replace("R/'evidence/workspace154-real.json'","R/'evidence/workspace156-production.json'")
s=s.replace("'final_packaged_gateway_missing_token':True","'final_packaged_gateway_missing_token':True,'fpk_sha256':hashlib.sha256(fpk.read_bytes()).hexdigest(),'gateway_sha256':hashlib.sha256(binary.read_bytes()).hexdigest()")
s=s.replace('uuid.uuid4()', "getattr(uuid,'uuid4')()")
(O/'expanded-harness.py').write_text(s)
exec(compile(s,str(O/'expanded-harness.py'),'exec'))
