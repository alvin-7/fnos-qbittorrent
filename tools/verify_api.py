import pathlib,urllib.request,urllib.parse,http.cookiejar,json,subprocess,time
r=pathlib.Path(__file__).resolve().parents[1];base='http://127.0.0.1:18080';cj=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj));report={}
def req(path,data=None,headers={},client=op):
 if isinstance(data,dict):data=urllib.parse.urlencode(data).encode()
 try:
  x=client.open(urllib.request.Request(base+path,data=data,headers=headers),timeout=10);return x.status,x.read()
 except urllib.error.HTTPError as e:return e.code,e.read()
status,body=req('/api/v2/app/version'); assert status==403; report['unauthenticated']=status
password=(r/'.runtime/password').read_text().strip()
assert req('/api/v2/auth/login',{'username':'admin','password':password})[0]==204
status,body=req('/api/v2/app/version'); assert status==200 and body==b'v5.2.4'; report['version']=body.decode()
status,body=req('/api/v2/torrents/info'); assert status==200; report['authenticated']=status
assert req('/api/v2/app/version',headers={'Host':'attacker.invalid:18080'})[0] in (401,403); report['bad_host']=req('/api/v2/app/version',headers={'Host':'attacker.invalid:18080'})[0]
assert req('/api/v2/torrents/stop',{'hashes':'all'},headers={'Origin':'https://attacker.invalid'})[0] in (401,403); report['csrf_origin']=req('/api/v2/torrents/stop',{'hashes':'all'},headers={'Origin':'https://attacker.invalid'})[0]
prefs=json.loads(req('/api/v2/app/preferences')[1]); assert prefs['web_ui_csrf_protection_enabled'] and prefs['web_ui_host_header_validation_enabled']; report['security_preferences']='enabled'
torrents=json.loads(body); assert torrents; report['tasks']=len(torrents)
for action in ['stop','start']:
 status=req('/api/v2/torrents/'+action,{'hashes':torrents[0]['hash']})[0]; assert status in (200,204); report[action]=status
(r/'evidence/api-security.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
