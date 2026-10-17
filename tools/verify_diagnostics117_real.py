import pathlib,os,subprocess,time,re,urllib.request,urllib.parse,shutil
R=pathlib.Path(__file__).resolve().parents[1];D=R/'.runtime/diagnostics117';D.mkdir(exist_ok=True);rt=R/'.runtime/package117/app/runtime';C=D/'qBittorrent/config';C.mkdir(parents=True,exist_ok=True)
(C/'qBittorrent.conf').write_text('[BitTorrent]\nSession\\DHTEnabled=false\nSession\\PeXEnabled=false\nSession\\LSDEnabled=false\n[Network]\nPortForwardingEnabled=false\n[Preferences]\nWebUI\\Address=127.0.0.1\nWebUI\\Port=18126\nWebUI\\HostHeaderValidation=true\nWebUI\\CSRFProtection=true\nWebUI\\ServerDomains=127.0.0.1\n')
f=open(D/'private-process.log','w');os.chmod(D/'private-process.log',0o600)
p=subprocess.Popen([str(rt/'lib/ld-musl-x86_64.so.1'),'--library-path',f'{rt}/lib:{rt}/usr/lib:{rt}/usr/lib/libproxy',str(rt/'usr/bin/qbittorrent-nox'),'--profile='+str(D),'--confirm-legal-notice'],stdout=f,stderr=f,env=dict(os.environ,QT_PLUGIN_PATH=str(rt/'usr/lib/qt6/plugins')))
try:
 for _ in range(100):
  time.sleep(.1);m=re.search(r'session: (\S+)',(D/'private-process.log').read_text())
  if m:break
 else:raise RuntimeError('readiness failure (raw output suppressed)')
 req=urllib.request.Request('http://127.0.0.1:18126/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':m[1]}).encode(),headers={'Host':'127.0.0.1:18126'})
 cookie=urllib.request.urlopen(req).headers['Set-Cookie'].split(';')[0]
 env=dict(os.environ,GO111MODULE='off',DIAGNOSTIC_TEST_BACKEND='http://127.0.0.1:18126',DIAGNOSTIC_TEST_COOKIE=cookie,DIAGNOSTIC_TEST_SAVE=str(D/'downloads'))
 result=subprocess.run(['go','test','./gateway','-run','TestRealDiagnosticAcquisition','-v'],env=env,cwd=R,capture_output=True,text=True)
 print(result.stdout);print(result.stderr);assert result.returncode==0
 subprocess.run(['node','tools/verify_diagnostics117_browser.mjs'],env=env,cwd=R,check=True)
finally:p.terminate();p.wait(timeout=20);f.close()
