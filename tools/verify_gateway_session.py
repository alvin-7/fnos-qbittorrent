"""Real isolated qB 5.2.4 + Unix session adapter + browser security suite."""
import pathlib,subprocess,os,time,socket,http.client,json,shutil,re,urllib.parse
r=pathlib.Path(__file__).resolve().parents[1];d=r/'.runtime/session-security';d.mkdir(parents=True,exist_ok=True)
image='ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1';net='fnos-session-security';qb='fnos-session-core';gw='fnos-session-gateway';report={}
def run(*args):return subprocess.check_output(args,stderr=subprocess.STDOUT).decode().strip()
def request(path,method='GET',headers=None,body=None):
 c=http.client.HTTPConnection('localhost',timeout=5);c.sock=socket.socket(socket.AF_UNIX);c.sock.connect(str(d/'app.sock'));c.request(method,'/app/fnos-qbittorrent'+path,body,headers or {});res=c.getresponse();data=res.read();h=dict(res.getheaders());c.close();return res.status,data,h
try:
 for name in [qb,gw]:subprocess.run(['docker','rm','-f',name],capture_output=True)
 subprocess.run(['docker','network','rm',net],capture_output=True)
 run('docker','network','create','--internal','--subnet','172.30.247.0/29',net)
 (d/'downloads').mkdir(exist_ok=True)
 subprocess.run([str(r/'fnos-qbittorrent/cmd/prepare')],env=dict(os.environ,TRIM_PKGVAR=str(d),TRIM_DATA_SHARE_PATHS=str(d/'downloads')),check=True)
 subprocess.run(['go','build','-o',str(d/'gateway'),'./gateway'],cwd=r,env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
 run('docker','run','-d','--name',qb,'--network',net,'--ip','172.30.247.2','--network-alias','qbittorrent','-p','127.0.0.1:18082:18080','-e','QBT_LEGAL_NOTICE=confirm','-e','QBT_WEBUI_PORT=18080','-v',str(d/'config')+':/config','-v',str(d/'downloads')+':/downloads',image)
 run('docker','network','connect','bridge',qb)
 run('docker','run','-d','--name',gw,'--network',net,'--ip','172.30.247.3','--user',f'{os.getuid()}:{os.getgid()}','--cap-drop=ALL','--security-opt=no-new-privileges:true','-e','GATEWAY_SOCKET=/test/app.sock','-e','BACKEND_URL=http://qbittorrent:18080','-v',str(d)+':/test','--entrypoint','/test/gateway',image)
 for _ in range(50):
  try:
   c=http.client.HTTPConnection('127.0.0.1',18082,timeout=1);c.request('GET','/api/v2/app/version',headers={'Host':'127.0.0.1:18080'});res=c.getresponse();res.read();c.close()
   if res.status==403 and (d/'app.sock').exists():break
  except OSError:pass
  time.sleep(.3)
 else:raise RuntimeError('qB readiness timeout')
 report['direct_no_auth']=res.status
 c=http.client.HTTPConnection('127.0.0.1',18082,timeout=5);c.request('POST','/api/v2/app/setPreferences','json=%7B%7D',{'Host':'127.0.0.1:18080','X-Trim-Isadmin':'true','X-Trim-Userid':'1000','Content-Type':'application/x-www-form-urlencoded'});res=c.getresponse();report['direct_forged_trim']=res.status;res.read();c.close();assert report['direct_forged_trim']==403
 report['header_only_without_session']=request('/api/v2/app/setPreferences','POST',{'X-Trim-Isadmin':'true','X-Trim-Userid':'1000','Origin':'https://anything.example'},'json=%7B%7D')[0];assert report['header_only_without_session']==403
 b=request('/gateway/session','POST',{'X-Trim-Isadmin':'true','X-Trim-Userid':'1000','Origin':'https://arbitrary.example','X-Fnos-Bootstrap':'1'});assert b[0]==200
 token=json.loads(b[1])['token'];cookie=b[2]['Set-Cookie'].split(';')[0]
 report['https_cookie_policy']=all(x in b[2]['Set-Cookie'] for x in ['HttpOnly','Secure','SameSite=Strict','Path=/app/fnos-qbittorrent/']);assert report['https_cookie_policy']
 report['browser']=run('node',str(r/'tools/verify_gateway_session_browser.mjs'),str(d/'app.sock'))
 # Prove direct transport still uses native qB credentials (not gateway tokens).
 password=re.findall(r'temporary password is provided for this session: (\S+)',run('docker','logs',qb))[-1]
 c=http.client.HTTPConnection('127.0.0.1',18082,timeout=5);c.request('POST','/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':password}),{'Host':'127.0.0.1:18080','Content-Type':'application/x-www-form-urlencoded'});res=c.getresponse();native_cookie=res.getheader('Set-Cookie').split(';')[0];assert res.status==204;res.read();c.close()
 for name,host,origin,expected in [('native_authenticated','127.0.0.1:18080','http://127.0.0.1:18080',200),('native_bad_host','evil.example','http://127.0.0.1:18080',401),('native_bad_origin','127.0.0.1:18080','https://evil.example',401)]:
  c=http.client.HTTPConnection('127.0.0.1',18082,timeout=5);c.request('POST','/api/v2/app/setPreferences','json=%7B%7D',{'Host':host,'Origin':origin,'Cookie':native_cookie,'Content-Type':'application/x-www-form-urlencoded'});res=c.getresponse();report[name]=res.status;res.read();c.close();assert report[name]==expected
 run('docker','restart',gw)
 for _ in range(30):
  try:
   status=request('/api/v2/app/version','GET',{'X-Trim-Isadmin':'true','X-Trim-Userid':'1000','Origin':'https://arbitrary.example','Cookie':cookie,'X-Fnos-CSRF':token})[0]
   if status==403:break
  except OSError:pass
  time.sleep(.2)
 assert status==403;report['restart_invalidates_session']=True;report['passed']=True
finally:
 (r/'evidence/gateway-session-security.json').write_text(json.dumps(report,indent=2))
 for name in [gw,qb]:subprocess.run(['docker','rm','-f',name],capture_output=True)
 subprocess.run(['docker','network','rm',net],capture_output=True)
 if (d/'config').exists():shutil.rmtree(d/'config')
print(json.dumps(report,indent=2))
