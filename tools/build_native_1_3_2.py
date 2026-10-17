"""Immutable local TEST CANDIDATE; not a NAS-accepted or public release."""
from pathlib import Path
import hashlib,io,json,os,shutil,subprocess,tarfile
R=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'release/fnos-qbittorrent-native-1.2.8-x86_64.fpk';out=R/'release/fnos-qbittorrent-native-1.3.2-x86_64.fpk';stage=R/'.runtime/package132';overlay=R/'release/native-1.3.2-connector-source-overlay.tar.gz'
assert not out.exists() and not stage.exists() and not overlay.exists()
prior={str(p.relative_to(R)):sha(p) for p in (R/'release').glob('*.fpk') if p.is_file()}
stage.mkdir()
with tarfile.open(base) as t:t.extractall(stage,filter='data')
with tarfile.open(fileobj=io.BytesIO((stage/'app.tgz').read_bytes())) as t:t.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink();m=stage/'manifest';m.write_text('\n'.join(l.replace('1.2.8','1.3.2') for l in m.read_text().splitlines() if not l.startswith('checksum'))+'\n')
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ['public','private']:
 p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
sources=R/'.runtime/gateway132-native';sources.mkdir()
for f in (R/'gateway').glob('*.go'):
 if not f.name.endswith('_test.go'):(sources/f.name).write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
subprocess.run(['go','build','-trimpath','-o',str(stage/'app/bin/gateway'),*map(str,sources.glob('*.go'))],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
build=R/'.runtime/build132';build.mkdir();subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=build,check=True)
made=build/'fnos-qbittorrent-native.fpk';assert made.is_file();shutil.copyfile(made,out)
out.with_suffix('.fpk.sha256').write_text(sha(out)+'  '+out.name+'\n')
preserved=0
with tarfile.open(base) as old,tarfile.open(out) as new:
 with tarfile.open(fileobj=io.BytesIO(old.extractfile('app.tgz').read())) as oa,tarfile.open(fileobj=io.BytesIO(new.extractfile('app.tgz').read())) as na:
  files={m.name.removeprefix('./'):na.extractfile(m).read() for m in na if m.isfile()}
  for m in oa:
   if m.isfile():
    n=m.name.removeprefix('./')
    if not n.startswith('webui/') and n!='bin/gateway':assert files[n]==oa.extractfile(m).read(),n;preserved+=1
  for n,b in files.items():assert b==(stage/'app'/n).read_bytes(),n
assert all(sha(R/n)==h for n,h in prior.items())
paths=['src','gateway','docs/product','package.json','package-lock.json','tsconfig.json','index.html','tools/build_native_1_3_2.py','tools/test_connector132.mjs','tools/verify_connector130.py','tools/test_labels130.mjs','tools/test_label_batch130.mjs']
with tarfile.open(overlay,'w:gz') as t:
 for p in paths:t.add(R/p,arcname=p)
overlay.with_suffix('.gz.sha256').write_text(sha(overlay)+'  '+overlay.name+'\n')
report={'version':'1.3.2','status':'TEST_CANDIDATE_NOT_ACCEPTED','fpk_sha256':sha(out),'overlay_sha256':sha(overlay),'runtime_license_non_ui_preserved_files':preserved,'prior_artifacts_unchanged':prior,'exact_packaged_bytes_verified':True,'nas_verified':False,'full_acceptance':False,'gaps':['full connector security/rotation/restart matrix in Docker','final iframe desktop/mobile workflow','PT/ratio/diagnostics final package regression','NAS and physical phone acceptance','path mapping acceptance']}
(R/'evidence/native-package-audit-1.3.2.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
