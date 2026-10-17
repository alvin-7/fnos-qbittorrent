from pathlib import Path
import subprocess,os,json,urllib.request
R=Path(__file__).resolve().parents[1];A=R/'.runtime/package118/app';D=R/'.runtime/lifecycle118';D.mkdir(exist_ok=False);env=dict(os.environ,TRIM_APPDEST=str(A),TRIM_PKGVAR=str(D),TRIM_DATA_SHARE_PATHS=str(D/'downloads'));ctl=A/'bin/native-control'
def run(action):subprocess.run([str(ctl),action],env=env,check=True,capture_output=True)
def prefs():
 s=json.loads((D/'state.json').read_text());r=urllib.request.Request('http://127.0.0.1:18080/api/v2/app/preferences',headers={'Cookie':s['Cookie']});return json.load(urllib.request.urlopen(r))
try:
 run('start');p=prefs()
 for k,v in dict(listen_port=49160,random_port=False,dht=False,pex=False,lsd=False,upnp=False).items():assert p[k]==v,(k,p[k])
 fresh={k:p[k] for k in ['listen_port','random_port','dht','pex','lsd','upnp']};run('stop')
 conf=D/'profile/qBittorrent/config/qBittorrent.conf';s=conf.read_text();assert 'Session\\Port=49160' in s;conf.write_text(s.replace('Session\\Port=49160','Session\\Port=6881'))
 run('start');assert prefs()['listen_port']==6881;run('stop')
 report={'packaged_native_control_fresh_real_preferences':fresh,'existing_6881_survives_prepare_and_restart':True,'passed':True};(R/'evidence/port118-lifecycle.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
finally:
 if (D/'state.json').exists():run('stop')
