"""Real native backend UI boundary and package integrity audit (isolated fixture only)."""
from pathlib import Path
import urllib.request,json,tarfile,io,hashlib
R=Path(__file__).resolve().parents[1];A=R/'native-package/app';D=R/'.runtime/native-test';cookie=json.loads((D/'state.json').read_text())['Cookie']
report={}
for label,headers in [('unauthenticated',{}),('authenticated',{'Cookie':cookie})]:
 with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/',headers=headers)) as res:
  b=res.read();expected=(A/'webui'/('private' if headers else 'public')/'index.html').read_bytes();assert b==expected;report[label+'_root_exact_custom_ui']=True
try:urllib.request.urlopen('http://127.0.0.1:18080/api/v2/app/version');raise AssertionError('unauthenticated API')
except urllib.error.HTTPError as e:assert e.code==403
with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/api/v2/app/version',headers={'Cookie':cookie})) as res:assert res.read()==b'v5.2.4'
report['api_preserved_authenticated']=True
conf=(D/'profile/qBittorrent/config/qBittorrent.conf').read_text()
for s in ['WebUI\\Address=127.0.0.1','WebUI\\LocalHostAuth=true','WebUI\\AlternativeUIEnabled=true']:assert s in conf
report['private_backend_configuration']=True
p=R/'release/fnos-qbittorrent-native-1.1.3-x86_64.fpk';files={}
with tarfile.open(p) as tf:
 assert dict(line.split('=',1) for line in tf.extractfile('manifest').read().decode().splitlines() if '=' in line).get('version               ','').strip()=='1.1.3'
 with tarfile.open(fileobj=io.BytesIO(tf.extractfile('app.tgz').read())) as app:
  for m in app:
   if m.isfile():
    name=m.name.removeprefix('./');b=app.extractfile(m).read();local=A/name
    if not local.is_file():local=R/'native-package'/name
    assert local.is_file(),name;assert b==local.read_bytes(),name;files[name]=hashlib.sha256(b).hexdigest()
   else:assert not m.issym() and not m.islnk() and not m.isdev() and not m.isfifo(),m.name
assert any(x.endswith('DO-NOT-DISTRIBUTE.txt') for x in files)
report.update(files_verified=len(files),files=files,fpk_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),version='1.1.3',passed=True)
(R/'evidence/native-package-audit-1.1.3.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
