"""Stage 1.1.8 from immutable 1.1.7; publish only after external tests pass."""
from pathlib import Path
import tarfile,io,shutil,subprocess,os,hashlib,json,sys
R=Path(__file__).resolve().parents[1];stage=R/'.runtime/package118';old=R/'release/fnos-qbittorrent-native-1.1.7-x86_64.fpk';out=R/'release/fnos-qbittorrent-native-1.1.8-x86_64.fpk'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
if '--publish' not in sys.argv:
 assert not stage.exists();stage.mkdir()
 with tarfile.open(old) as t:
  t.extractall(stage,filter='data')
  with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:a.extractall(stage/'app',filter='data')
 (stage/'app.tgz').unlink()
 m=stage/'manifest';m.write_text('\n'.join(x.replace('1.1.7','1.1.8') for x in m.read_text().splitlines() if not x.startswith('checksum'))+'\n')
 subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
 for scope in ['public','private']:
  p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
  for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
 subprocess.run(['go','build','-trimpath','-o',str(stage/'app/bin/native-control'),str(R/'native/control.go')],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0',GOARCH='amd64'),check=True)
 # Existing lifecycle binary path is discovered from package main script.
 print((stage/'cmd/main').read_text());print('STAGED',stage);sys.exit()
assert not out.exists(),'immutable output exists'
for p in ['port118-browser.json','port118-persistence.json','port118-lifecycle.json']:
 assert json.loads((R/'evidence'/p).read_text())['passed']
# Lifecycle smoke leaves an inert Unix socket; never ship runtime sockets.
(stage/'app/app.sock').unlink(missing_ok=True)
src=stage/'app/licenses/ui-fix-1.1.8';assert not src.exists();src.mkdir()
for name in ['src','native','gateway']:shutil.copytree(R/name,src/name)
(src/'tools').mkdir()
for name in ['build_native_1_1_8.py','verify_port118_real.py','verify_port118_browser.mjs','verify_port118_lifecycle.py']:shutil.copyfile(R/'tools'/name,src/'tools'/name)
shutil.copyfile(R/'docs/native-1.1.8.md',src/'README.md')
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
    name=m.name.removeprefix('./')
    if not name.startswith('webui/') and name!='bin/native-control':assert new[name]==oa.extractfile(m).read(),name;preserved+=1
  for name,b in new.items():assert b==(stage/'app'/name).read_bytes();files[name]=hashlib.sha256(b).hexdigest()
report={'version':'1.1.8','sha256':sha(out),'bytes':out.stat().st_size,'original_non_ui_control_files_preserved':preserved,'packaged_files':len(files),'files':files,'passed':True}
(R/'evidence/native-package-audit-1.1.8.json').write_text(json.dumps(report,indent=2))
overlay=R/'release/native-1.1.8-ui-source-overlay.tar.gz';assert not overlay.exists()
with tarfile.open(overlay,'w:gz') as t:
 for name in ['src','native','gateway','tools/build_native_1_1_8.py','tools/verify_port118_real.py','tools/verify_port118_browser.mjs','tools/verify_port118_lifecycle.py','evidence/port118-lifecycle.json','evidence/port118-go-tests.txt','docs/native-1.1.8.md','evidence/port118-browser.json','evidence/port118-persistence.json','evidence/qb524-torrentscontroller.cpp','evidence/qb524-trackerentrystatus.h','package.json','package-lock.json','tsconfig.json','index.html']:t.add(R/name,arcname=name)
(overlay.with_suffix('.gz.sha256')).write_text(sha(overlay)+'  '+overlay.name+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2));print('overlay',sha(overlay))
