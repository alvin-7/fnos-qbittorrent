"""Immutable UI-only 1.2.8; retain previous releases and audit exact packaged bytes."""
from pathlib import Path
import hashlib, io, json, os, shutil, subprocess, tarfile
R=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior={str(p.relative_to(R)):sha(p) for v in ('1.2.5','1.2.6','1.2.7') for p in (R/'release').glob('*'+v+'*') if p.is_file()}
base=R/'release/fnos-qbittorrent-native-1.2.7-x86_64.fpk'
out=R/'release/fnos-qbittorrent-native-1.2.8-x86_64.fpk'
stage=R/'.runtime/package128'
overlay=R/'release/native-1.2.8-share-ratio-disable-source-overlay.tar.gz'
assert not out.exists() and not stage.exists() and not overlay.exists()
stage.mkdir()
with tarfile.open(base) as t:t.extractall(stage,filter='data')
with tarfile.open(fileobj=io.BytesIO((stage/'app.tgz').read_bytes())) as t:t.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink()
def inventory(root):
 return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
before=inventory(stage)
p=stage/'manifest';text=p.read_text();assert 'version               = 1.2.7' in text
p.write_text(text.replace('version               = 1.2.7','version               = 1.2.8'))
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ('public','private'):
 p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
after=inventory(stage)
changes={k:{'before':before.get(k),'after':after.get(k)} for k in sorted(before.keys()|after.keys()) if before.get(k)!=after.get(k)}
assert all(k=='manifest' or k.startswith('app/webui/') for k in changes), changes
builddir=R/'.runtime/build128';builddir.mkdir(exist_ok=False)
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=builddir,check=True)
made=builddir/'fnos-qbittorrent-native.fpk';assert made.is_file()
shutil.copyfile(made,out)
(out.with_suffix('.fpk.sha256')).write_text(sha(out)+'  '+out.name+'\n')
check=R/'.runtime/audit128';check.mkdir()
with tarfile.open(out) as t:t.extractall(check,filter='data')
with tarfile.open(fileobj=io.BytesIO((check/'app.tgz').read_bytes())) as t:t.extractall(check/'app',filter='data')
(check/'app.tgz').unlink()
packed=inventory(check);staged=inventory(stage)
assert {k:v for k,v in packed.items() if k!='manifest'}=={k:v for k,v in staged.items() if k!='manifest'}
without_checksum=lambda p:'\n'.join(l for l in p.read_text().splitlines() if not l.startswith('checksum'))
assert without_checksum(check/'manifest')==without_checksum(stage/'manifest')
assert all(sha(R/p)==h for p,h in prior.items())
files=['src/Settings.tsx','src/pt.ts','tests/share-ratio.spec.ts','tools/build_native_1_2_8.py','tools/verify_regression128.py','tools/verify_ratio128.py','tools/verify_ratio128.mjs']
with tarfile.open(overlay,'w:gz') as t:
 for p in files:t.add(R/p,arcname=p)
overlay.with_suffix('.tar.gz.sha256').write_text(sha(overlay)+'  '+overlay.name+'\n')
report={'version':'1.2.8','base':str(base.relative_to(R)),'fpk_sha256':sha(out),'overlay_sha256':sha(overlay),'bytes':out.stat().st_size,'prior_artifacts':prior,'prior_artifacts_unchanged':True,'exact_package_matches_stage':True,'changed_files':changes,'source_sha256':{p:sha(R/p) for p in files},'nas_verified':False}
(R/'evidence/native-package-audit-1.2.8.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print(json.dumps(report,indent=2,ensure_ascii=False))
