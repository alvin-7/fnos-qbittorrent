"""Immutable UI-only candidate, inheriting runtime/gateway/control/license bytes."""
from pathlib import Path
import tarfile,io,shutil,subprocess,os,hashlib,json,sys
R=Path(__file__).resolve().parents[1];stage=R/'.runtime/package119';old=R/'release/fnos-qbittorrent-native-1.1.8-x86_64.fpk';out=R/'release/fnos-qbittorrent-native-1.1.9-x86_64.fpk'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not out.exists(),'immutable output exists; choose next version'
if '--publish' not in sys.argv:
 assert not stage.exists();stage.mkdir()
 with tarfile.open(old) as t:
  t.extractall(stage,filter='data')
  with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:a.extractall(stage/'app',filter='data')
 (stage/'app.tgz').unlink()
 m=stage/'manifest';m.write_text('\n'.join(x.replace('1.1.8','1.1.9') for x in m.read_text().splitlines() if not x.startswith('checksum'))+'\n')
 subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
 for scope in ['public','private']:
  p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
  for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
 sources=R/'.runtime/gateway119';sources.mkdir(exist_ok=True)
 for f in (R/'gateway').glob('*.go'):
  if not f.name.endswith('_test.go'):(sources/f.name).write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
 subprocess.run(['go','build','-trimpath','-o',str(stage/'app/bin/gateway'),*map(str,sources.glob('*.go'))],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
 print('STAGED',stage);sys.exit()
for p in ['pt119-real.json','pt119-browser.json','pt119-regression.json']:
 assert json.loads((R/'evidence'/p).read_text())['passed'],p
src=stage/'app/licenses/pt-1.1.9';assert not src.exists();src.mkdir()
for n in ['src','gateway','native']:shutil.copytree(R/n,src/n)
shutil.copytree(R/'tools',src/'tools',ignore=shutil.ignore_patterns('fnpack','__pycache__'))
shutil.copyfile(R/'docs/native-1.1.9.md',src/'README.md')
(stage/'app/app.sock').unlink(missing_ok=True)
(R/'fnos-qbittorrent-native.fpk').unlink(missing_ok=True)
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=R,check=True)
p=R/'fnos-qbittorrent-native.fpk';assert p.is_file();shutil.copyfile(p,out)
(out.with_suffix('.fpk.sha256')).write_text(sha(out)+'  '+out.name+'\n')
files={};preserved=0
with tarfile.open(old) as ot,tarfile.open(out) as nt:
 with tarfile.open(fileobj=io.BytesIO(ot.extractfile('app.tgz').read())) as oa,tarfile.open(fileobj=io.BytesIO(nt.extractfile('app.tgz').read())) as na:
  new={m.name.removeprefix('./'):na.extractfile(m).read() for m in na if m.isfile()}
  for m in oa:
   if m.isfile():
    n=m.name.removeprefix('./')
    if not n.startswith('webui/') and n!='bin/gateway':assert new[n]==oa.extractfile(m).read(),n;preserved+=1
  for n,b in new.items():assert b==(stage/'app'/n).read_bytes();files[n]=hashlib.sha256(b).hexdigest()
report={'version':'1.1.9','sha256':sha(out),'bytes':out.stat().st_size,'all_previous_non_ui_files_preserved':preserved,'files':files,'passed':True}
(R/'evidence/native-package-audit-1.1.9.json').write_text(json.dumps(report,indent=2))
overlay=R/'release/native-1.1.9-ui-source-overlay.tar.gz';assert not overlay.exists()
with tarfile.open(overlay,'w:gz') as t:
 for n in ['src','native','gateway','tools','docs/native-1.1.9.md','package.json','package-lock.json','tsconfig.json','index.html']:
  t.add(R/n,arcname=n,filter=lambda m:None if '/__pycache__' in m.name or m.name=='tools/fnpack' else m)
 for p in (R/'evidence').glob('*119*'):t.add(p,arcname='evidence/'+p.name)
 for p in (R/'evidence').glob('qb524-*'):t.add(p,arcname='evidence/'+p.name)
(overlay.with_suffix('.gz.sha256')).write_text(sha(overlay)+'  '+overlay.name+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2));print('overlay',sha(overlay))
