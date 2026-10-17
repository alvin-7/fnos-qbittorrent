"""Immutable native 1.2.9 label/category UI release; never overwrite prior artifacts."""
from pathlib import Path
import hashlib,io,json,os,shutil,subprocess,tarfile
R=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=R/'release/fnos-qbittorrent-native-1.2.8-x86_64.fpk'
out=R/'release/fnos-qbittorrent-native-1.2.9-x86_64.fpk'
stage=R/'.runtime/package129'
overlay=R/'release/native-1.2.9-labels-source-overlay.tar.gz'
assert base.is_file() and not out.exists() and not stage.exists() and not overlay.exists()
stage.mkdir()
with tarfile.open(base) as t:t.extractall(stage,filter='data')
with tarfile.open(fileobj=io.BytesIO((stage/'app.tgz').read_bytes())) as t:t.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink()
def inventory(root):return {str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
before=inventory(stage)
p=stage/'manifest';text=p.read_text();assert 'version               = 1.2.8' in text
p.write_text(text.replace('version               = 1.2.8','version               = 1.2.9').replace('changelog             =','changelog             = 标签分类：qB 标准 API，MoviePilot 兼容；'))
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ('public','private'):
 p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
after=inventory(stage)
changes={k:{'before':before.get(k),'after':after.get(k)} for k in sorted(before.keys()|after.keys()) if before.get(k)!=after.get(k)}
assert all(k=='manifest' or k.startswith('app/webui/') for k in changes),changes
builddir=R/'.runtime/build129';builddir.mkdir(exist_ok=False)
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=builddir,check=True)
made=builddir/'fnos-qbittorrent-native.fpk';assert made.is_file();shutil.copyfile(made,out)
(out.with_suffix('.fpk.sha256')).write_text(sha(out)+'  '+out.name+'\n')
check=R/'.runtime/audit129';check.mkdir()
with tarfile.open(out) as t:t.extractall(check,filter='data')
with tarfile.open(fileobj=io.BytesIO((check/'app.tgz').read_bytes())) as t:t.extractall(check/'app',filter='data')
(check/'app.tgz').unlink();packed=inventory(check);staged=inventory(stage)
assert {k:v for k,v in packed.items() if k!='manifest'}=={k:v for k,v in staged.items() if k!='manifest'}
without_checksum=lambda p:'\n'.join(l for l in p.read_text().splitlines() if not l.startswith('checksum'))
assert without_checksum(check/'manifest')==without_checksum(stage/'manifest')
files=['src/api.ts','src/tags.ts','src/Labels.tsx','src/TorrentList.tsx','src/AddTask.tsx','src/main.tsx','src/style.css','docs/product/UI_REDESIGN_OPENDESIGN.md','tools/build_native_1_2_9.py']
with tarfile.open(overlay,'w:gz') as t:
 for f in files:t.add(R/f,arcname=f)
(overlay.with_suffix('.tar.gz.sha256')).write_text(sha(overlay)+'  '+overlay.name+'\n')
report={'version':'1.2.9','base':str(base.relative_to(R)),'fpk_sha256':sha(out),'overlay_sha256':sha(overlay),'bytes':out.stat().st_size,'prior_1_2_8_sha256':sha(base),'exact_package_matches_stage':True,'changed_files':changes,'source_sha256':{f:sha(R/f) for f in files},'nas_verified':False,'real_qb_api_suite':'not run in this environment'}
(R/'evidence/native-package-audit-1.2.9.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,indent=2,ensure_ascii=False))
