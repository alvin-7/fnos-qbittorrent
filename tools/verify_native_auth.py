"""Real pinned native qB + packaged gateway; isolated test profile only."""
from pathlib import Path
import os,json,subprocess,http.server,http.client,socket,threading,urllib.parse,time
R=Path(__file__).resolve().parents[1];D=R/'.runtime/native-test';A=R/'native-package/app';P='/app/fnos-qbittorrent-native'; report={};counts={};backend_cookie=''
class Bridge(http.server.BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def do_GET(self):self.forward()
 def do_POST(self):self.forward()
 def forward(self):
  global backend_cookie
  counts[self.path]=counts.get(self.path,0)+1
  c=http.client.HTTPConnection('127.0.0.1',18080,timeout=5);body=self.rfile.read(int(self.headers.get('Content-Length',0)));h=dict(self.headers);h['Host']='127.0.0.1:18080';c.request(self.command,self.path,body,h);r=c.getresponse();data=r.read()
  if self.path=='/api/v2/auth/login':report['last_login_status']=r.status;report['last_login_cookie_names']=[x.split('=',1)[0] for x in (r.getheader('Set-Cookie') or '').split(';')[:1]]
  if self.path=='/api/v2/auth/login' and r.getheader('Set-Cookie'):backend_cookie=r.getheader('Set-Cookie').split(';')[0]
  self.send_response(r.status)
  for k,v in r.getheaders():
   if k.lower() not in ['transfer-encoding','connection','content-length']:self.send_header(k,v)
  self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);c.close()
bridge=http.server.ThreadingHTTPServer(('127.0.0.1',18084),Bridge);threading.Thread(target=bridge.serve_forever,daemon=True).start()
pw=D/'test-gateway-password';pw.write_bytes((D/'backend-password').read_bytes());pw.chmod(0o600);sock=str(D/'auth-test.sock');log=open(D/'auth-test.log','w');env=dict(os.environ,BACKEND_URL='http://127.0.0.1:18084',BACKEND_COOKIE='SID_expired=invalid',BACKEND_PASSWORD_FILE=str(pw),GATEWAY_SOCKET=sock)
p=subprocess.Popen([str(A/'bin/gateway')],env=env,stdout=log,stderr=log)
class Unix(http.client.HTTPConnection):
 def connect(self):self.sock=socket.socket(socket.AF_UNIX);self.sock.connect(sock)
cookie='';token=''
def req(method,path,fields=None):
 global cookie
 c=Unix('local',timeout=10);h={'Origin':'http://local','X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-Bootstrap':'1','X-Fnos-CSRF':token,'Cookie':cookie};body=None
 if fields is not None:body=urllib.parse.urlencode(fields);h['Content-Type']='application/x-www-form-urlencoded'
 c.request(method,P+path,body,h);r=c.getresponse();data=r.read()
 if r.getheader('Set-Cookie'):cookie=r.getheader('Set-Cookie').split(';')[0]
 code=r.status;c.close();return code,data
ctl_env=dict(os.environ,TRIM_APPDEST=str(A),TRIM_PKGVAR=str(D),TRIM_DATA_SHARE_PATHS=str(D/'downloads'))
def ctl(action):assert subprocess.run([str(R/'native-package/cmd/main'),action],env=ctl_env,capture_output=True).returncode==0
try:
 for _ in range(50):
  if Path(sock).exists():break
  time.sleep(.1)
 code,b=req('POST','/gateway/session');assert code==200;token=json.loads(b)['token']
 first=req('GET','/api/v2/app/version');assert first==(200,b'v5.2.4'),(first,counts,report);assert counts['/api/v2/auth/login']==1;report['expired_initial_sid_reauthenticated']=True
 # Logout actual gateway backend SID, not application session, then issue mutation.
 def expire():
  c=http.client.HTTPConnection('127.0.0.1',18080,timeout=5);c.request('POST','/api/v2/auth/logout','',{'Cookie':backend_cookie});r=c.getresponse();r.read();c.close();assert r.status==200
 expire();n=counts.get('/api/v2/app/setPreferences',0)
 assert req('POST','/api/v2/app/setPreferences',{'json':json.dumps({'dl_limit':334848})})[0]==200
 assert counts['/api/v2/app/setPreferences']==n+1;assert counts['/api/v2/auth/login']==2
 assert json.loads(req('GET','/api/v2/app/preferences')[1])['dl_limit']==334848;report['forced_backend_expiry_mutation_once']=True
 for key in ['web_ui_username','web_ui_password','web_ui_localhost_auth','web_ui_auth_subnet_whitelist_enabled']:
  assert req('POST','/api/v2/app/setPreferences',{'json':json.dumps({key:'blocked'})})[0]==403
 assert counts['/api/v2/app/setPreferences']==n+1;report['credential_changes_blocked_before_backend']=True
 ctl('stop');ctl('start');assert req('GET','/api/v2/app/version')==(200,b'v5.2.4');assert counts['/api/v2/auth/login']==3;report['real_backend_restart_reauthenticated']=True
 expire();pw.write_text('intentionally-wrong-local-fixture');before=counts['/api/v2/auth/login']
 for _ in range(5):assert req('POST','/api/v2/app/setPreferences',{'json':'{"dl_limit":1}'})[0]==503
 assert counts['/api/v2/auth/login']==before+1 and counts['/api/v2/app/setPreferences']==n+1;report['wrong_credentials_one_attempt_no_mutation']=True
 log.flush();text=(D/'auth-test.log').read_text();assert (D/'backend-password').read_text() not in text and backend_cookie not in text;report['credentials_not_logged']=True
 report['counts']=counts;report['passed']=True
 (R/'evidence/native-auth-1.1.1.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
finally:p.terminate();p.wait(timeout=10);log.close();bridge.shutdown();pw.unlink(missing_ok=True);Path(sock).unlink(missing_ok=True)
