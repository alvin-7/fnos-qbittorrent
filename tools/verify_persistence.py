import pathlib,urllib.request,urllib.parse,http.cookiejar,json,subprocess,time,re
r=pathlib.Path(__file__).resolve().parents[1];base='http://127.0.0.1:18080';result={}
def login():
 op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));p=(r/'.runtime/password').read_text().strip();op.open(base+'/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':p}).encode()).read();return op
a=login();before=json.loads(a.open(base+'/api/v2/torrents/info').read());prefs=json.loads(a.open(base+'/api/v2/app/preferences').read());assert before
subprocess.run(['docker','restart','fnos-qbt-test'],check=True,capture_output=True)
for _ in range(30):
 time.sleep(1);text=subprocess.check_output(['docker','logs','fnos-qbt-test'],stderr=subprocess.STDOUT).decode();ms=re.findall(r'temporary password is provided for this session: (\S+)',text)
 try:
  a=login();after=json.loads(a.open(base+'/api/v2/torrents/info').read());break
 except Exception: pass
 if ms:
  (r/'.runtime/password').write_text(ms[-1])
  try:a=login();after=json.loads(a.open(base+'/api/v2/torrents/info').read());break
  except Exception:pass
else:raise RuntimeError('restart login failed')
newprefs=json.loads(a.open(base+'/api/v2/app/preferences').read());assert sorted(t['hash'] for t in before)==sorted(t['hash'] for t in after)
for key in ['save_path','dl_limit','up_limit']:assert prefs[key]==newprefs[key]
assert (r/'.runtime/downloads/legal-test.txt').is_file();result={'restart_exit':0,'tasks_persisted':len(after),'settings_persisted':['save_path','dl_limit','up_limit'],'download_file_retained':True};(r/'evidence/persistence.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
