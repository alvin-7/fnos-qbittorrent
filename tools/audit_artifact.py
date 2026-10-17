import pathlib,tarfile,io,json,hashlib,re
r=pathlib.Path(__file__).resolve().parents[1];version=(r/'fnos-qbittorrent/manifest').read_text().split('version=',1)[1].splitlines()[0].strip();p=r/f'release/fnos-qbittorrent-{version}-x86_64.fpk';scanned=[]
with tarfile.open(p) as t:
 files={x.name:t.extractfile(x).read() for x in t.getmembers() if x.isfile()}
 with tarfile.open(fileobj=io.BytesIO(files['app.tgz'])) as app:
  for x in app.getmembers():
   if x.isfile():files['app/'+x.name]=app.extractfile(x).read()
secret=(r/'.runtime/password').read_bytes().strip()
for name,data in files.items():
 assert secret not in data, 'isolated secret leaked: '+name
 assert not any(x in name for x in ['.runtime','node_modules','.DS_Store']),name
 scanned.append(name)
assert any('webui/public/index.html' in n for n in scanned);assert any('webui/private/index.html' in n for n in scanned)
result={'fpk':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'size':p.stat().st_size,'file_count':len(scanned),'isolated_password_absent':True,'public_private_ui_included':True,'licenses_included':any('licenses/GPL-3.0' in n for n in scanned)}
(r/'evidence/package-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
