"""Read-only final artifact/source audit, plus hashed post-build verification overlay."""
from pathlib import Path
import hashlib,tarfile,io,json
R=Path(__file__).resolve().parents[1];E=R/'evidence';P=R/'release/fnos-qbittorrent-native-1.4.0-x86_64.fpk';S=R/'release/native-1.4.0-source-bundle.tar.gz'
sha=lambda b:hashlib.sha256(b).hexdigest()
with tarfile.open(P) as t:
 manifest=t.extractfile('manifest').read().decode();assert '1.4.0' in manifest
 app=t.extractfile('app.tgz').read()
with tarfile.open(fileobj=io.BytesIO(app)) as t:
 files={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
checks=[]
for name,data in files.items():
 p=R/'.runtime/package140/app'/name
 assert p.is_file() and p.read_bytes()==data,name
 if name.startswith(('webui/','bin/')):checks.append({'path':name,'sha256':sha(data)})
for scope in ['public','private']:
 for p in (R/'dist').rglob('*'):
  if not p.is_file():continue
  data=p.read_bytes()
  if p.suffix=='.js':data=data.replace(b'/app/fnos-qbittorrent',b'/app/fnos-qbittorrent-native')
  assert files['webui/'+scope+'/'+p.relative_to(R/'dist').as_posix()]==data
with tarfile.open(S) as t:
 members={m.name.removeprefix('./'):m for m in t if m.isfile()}
 for root in ['src','gateway','public']:
  for p in (R/root).rglob('*'):
   if p.is_file():assert t.extractfile(members['application-source/'+p.relative_to(R).as_posix()]).read()==p.read_bytes(),str(p)
 binding=json.loads(files['licenses/SOURCE-MANIFEST.json']);assert binding['sha256']==sha(S.read_bytes())
old=R/'release/fnos-qbittorrent-native-1.3.9-x86_64.fpk';expected=(old.with_suffix('.fpk.sha256')).read_text().split()[0];assert sha(old.read_bytes())==expected
# Verification scripts added after source freeze are supplied separately, not hidden inside an old immutable source archive.
overlay=R/'release/native-1.4.0-verification-overlay.tar.gz';assert not overlay.exists()
paths=[p for p in (R/'tools').glob('*140*')]+[p for p in E.iterdir() if '140' in p.name]+[Path(__file__)]
with tarfile.open(overlay,'w:gz') as t:
 for p in sorted(set(paths)):t.add(p,arcname=p.relative_to(R).as_posix())
report={'version':'1.4.0','status':'PASS','fpk_sha256':sha(P.read_bytes()),'source_sha256':sha(S.read_bytes()),'verification_overlay_sha256':sha(overlay.read_bytes()),'packaged_files_compared':len(files),'artifact_stage_exact_match':True,'source_current_src_gateway_public_exact_match':True,'dist_native_prefix_exact_match':True,'source_binding_exact_match':True,'prior_139_unchanged':True,'tested_runtime_and_ui':checks,'UNVERIFIED':['NAS installation/ACL/lifecycle and actual NAS tasks (intentionally not accessed)','physical phone/WebView safe-area rendering','complete MoviePilot application/path mapping and full connector matrix; isolated pinned client key APIs only','source bundle full offline reproducibility and license legal sufficiency not re-audited']}
(E/'selection140-artifact-audit.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='tested_runtime_and_ui'},indent=2))
