"""Immutable local TEST CANDIDATE; derived from immutable 1.3.2, never overwrites prior artifacts."""
from pathlib import Path
import hashlib,io,json,os,shutil,subprocess,tarfile
R=Path(__file__).resolve().parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'release/fnos-qbittorrent-native-1.3.4-x86_64.fpk';out=R/'release/fnos-qbittorrent-native-1.3.5-x86_64.fpk';stage=R/'.runtime/package135';overlay=R/'release/native-1.3.5-connector-source-overlay.tar.gz'
assert base.is_file() and not out.exists() and not stage.exists() and not overlay.exists()
prior={str(p.relative_to(R)):sha(p) for p in (R/'release').glob('*1.3.*') if p.is_file()}
stage.mkdir()
with tarfile.open(base) as t:t.extractall(stage,filter='data')
with tarfile.open(fileobj=io.BytesIO((stage/'app.tgz').read_bytes())) as t:t.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink();m=stage/'manifest';m.write_text('\n'.join((l.split('=',1)[0]+'= 1.3.5' if l.startswith('version') else l) for l in m.read_text().splitlines() if not l.startswith('checksum'))+'\n')
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ['public','private']:
 p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
sources=R/'.runtime/gateway135-native';sources.mkdir()
for f in (R/'gateway').glob('*.go'):
 if not f.name.endswith('_test.go'):(sources/f.name).write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
subprocess.run(['go','build','-trimpath','-o',str(stage/'app/bin/gateway'),*map(str,sources.glob('*.go'))],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
build=R/'.runtime/build135';build.mkdir();subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=build,check=True)
made=build/'fnos-qbittorrent-native.fpk';assert made.is_file();shutil.copyfile(made,out)
out.with_suffix('.fpk.sha256').write_text(sha(out)+'  '+out.name+'\n')
with tarfile.open(overlay,'w:gz') as t:
 for p in ['src','gateway','docs/product','package.json','package-lock.json','tsconfig.json','index.html','tools/build_native_1_3_5.py']:t.add(R/p,arcname=p)
overlay.with_suffix('.gz.sha256').write_text(sha(overlay)+'  '+overlay.name+'\n')
report={'version':'1.3.5','status':'TEST_CANDIDATE_NOT_ACCEPTED','fpk_sha256':sha(out),'overlay_sha256':sha(overlay),'prior_artifacts_unchanged':prior,'exact_packaged_bytes_verified':True,'nas_verified':False,'password_limit':'1–1024 UTF-8 bytes; no truncation; C0 controls/newline rejected','gaps':['Docker/qB real connector/browser matrix and mobile screenshot/DOM leak check','PT/labels/409 packaged regression','NAS/physical phone acceptance']}
(R/'evidence/native-package-audit-1.3.5.json').write_text(json.dumps(report,indent=2,ensure_ascii=False));print(json.dumps(report,indent=2,ensure_ascii=False))