"""Immutable UI + safe read-only gateway diagnostics, derived from exact 1.1.4."""
from pathlib import Path
import tarfile,io,shutil,subprocess,os,hashlib,json
R=Path(__file__).resolve().parents[1];out=R/'release/fnos-qbittorrent-native-1.1.7-x86_64.fpk';stage=R/'.runtime/package117'
assert not out.exists(), 'immutable artifact exists'
assert not stage.exists(), 'staging exists'
stage.mkdir()
old=R/'release/fnos-qbittorrent-native-1.1.4-x86_64.fpk'
with tarfile.open(old) as t:
 t.extractall(stage,filter='data')
 with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:a.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink()
m=stage/'manifest';m.write_text('\n'.join(x.replace('= 1.1.4','= 1.1.7') for x in m.read_text().splitlines() if not x.startswith('checksum'))+'\n')
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ['public','private']:
 p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
g=R/'.runtime/gateway117-src';g.mkdir()
for name in ['proxy.go','session.go','native.go','diagnostics.go']:
 s=(R/'gateway'/name).read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native').replace('http://qbittorrent:18080','http://127.0.0.1:18080');(g/name).write_text(s)
subprocess.run(['go','build','-trimpath','-o',str(stage/'app/bin/gateway'),*[str(x) for x in g.glob('*.go')]],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0',GOARCH='amd64'),check=True)
src=stage/'app/licenses/ui-fix-1.1.7';src.mkdir()
for n in ['src','tools']:
 (src/n).mkdir()
for n in ['AddTask.tsx','api.ts','main.tsx']:shutil.copyfile(R/'src'/n,src/'src'/n)
for n in ['verify_add_feedback.mjs','verify_add_native_real.mjs','build_native_1_1_6.py']:shutil.copyfile(R/'tools'/n,src/'tools'/n)
shutil.copytree(R/'gateway',src/'gateway')
for n in ['verify_diagnostics117_real.py','verify_diagnostics117_browser.mjs','verify_diagnostics117_state.mjs']:shutil.copyfile(R/'tools'/n,src/'tools'/n)
(src/'README.txt').write_text('UI + gateway safe diagnostics local candidate. qB/runtime and all 1.1.4 license/source material retained byte-for-byte. Gateway rebuilt from included source. Corresponding runtime source: native-1.1.4-sources.tar.gz (retain adjacent); full code overlay source is also supplied separately. No NAS validation or public distribution approval.\n')
oldoutput=R/'fnos-qbittorrent-native.fpk';oldoutput.unlink(missing_ok=True)
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=R,check=True)
assert oldoutput.is_file();shutil.copyfile(oldoutput,out)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(out.with_suffix('.fpk.sha256')).write_text(sha(out)+'  '+out.name+'\n')
# Verify all original non-WebUI files, including complete licensing tree, are unchanged.
files={};unchanged=0
with tarfile.open(old) as ot,tarfile.open(out) as nt:
 with tarfile.open(fileobj=io.BytesIO(ot.extractfile('app.tgz').read())) as oa,tarfile.open(fileobj=io.BytesIO(nt.extractfile('app.tgz').read())) as na:
  new={m.name.removeprefix('./'):na.extractfile(m).read() for m in na if m.isfile()}
  for member in oa:
   if member.isfile():
    name=member.name.removeprefix('./')
    if not name.startswith('webui/') and name!='bin/gateway':
     assert new[name]==oa.extractfile(member).read(),name;unchanged+=1
  for name,b in new.items():assert b==(stage/'app'/name).read_bytes();files[name]=hashlib.sha256(b).hexdigest()
report={'version':'1.1.7','sha256':sha(out),'bytes':out.stat().st_size,'original_non_ui_files_preserved':unchanged,'packaged_files':len(files),'files':files,'passed':True}
(R/'evidence/native-package-audit-1.1.7.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
overlay=R/'release/native-1.1.7-ui-source-overlay.tar.gz';assert not overlay.exists()
with tarfile.open(overlay,'w:gz') as t:
 for name in ['gateway','src','tools/verify_diagnostics117_browser.mjs','tools/verify_diagnostics117_real.py','tools/verify_diagnostics117_state.mjs','tools/verify_add_feedback.mjs','tools/verify_add_native_real.mjs','tools/build_native_1_1_6.py','package.json','package-lock.json','tsconfig.json','index.html']:
  t.add(R/name,arcname=name)
(overlay.with_suffix('.gz.sha256')).write_text(sha(overlay)+'  '+overlay.name+'\n')
