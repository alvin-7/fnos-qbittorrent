"""Immutable local 1.5.5 runtime-locked build; not a clean-runtime rebuild."""
from pathlib import Path
import hashlib,io,json,os,shutil,subprocess,tarfile
R=Path(__file__).resolve().parents[1];REL=R/'release';V='1.5.6';D=R/'.runtime/directory156-build';stage=R/'.runtime/package156';out=REL/f'fnos-qbittorrent-native-{V}-x86_64.fpk';source=REL/f'native-{V}-source-bundle.tar.gz'
for p in [D,stage,out,source]:assert not p.exists(),p
D.mkdir();stage.mkdir();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();base=REL/'fnos-qbittorrent-native-1.4.8-x86_64.fpk';prior={str(p):sha(p) for p in REL.iterdir() if p.is_file()}
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
with tarfile.open(base) as t:t.extractall(stage,filter='data')
with tarfile.open(fileobj=io.BytesIO((stage/'app.tgz').read_bytes())) as t:t.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink()
for scope in ['public','private']:
 dst=stage/'app/webui'/scope;shutil.rmtree(dst);shutil.copytree(R/'dist',dst)
 for p in dst.rglob('*.js'):p.write_text(p.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
g=D/'gateway';g.mkdir()
for p in (R/'gateway').glob('*.go'):
 if not p.name.endswith('_test.go'):(g/p.name).write_text(p.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
subprocess.run(['go','build','-trimpath','-ldflags','-s -w','-o',str(stage/'app/bin/gateway'),*map(str,g.glob('*.go'))],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
# The current template, not the historical runtime, owns resource declarations.
from audit_resource153 import audit,SCOPES,SHARES
data=json.loads((R/'native-package/config/resource').read_text())
assert data['api-scope']==SCOPES and data['data-share']==SHARES
for resource in [stage/'config/resource',stage/'app/config/resource']:
 resource.parent.mkdir(exist_ok=True);resource.write_text(json.dumps(data)+'\n')
native_sources=[str(p) for p in (R/'native').glob('*.go') if not p.name.endswith('_test.go')]
subprocess.run(['go','build','-trimpath','-ldflags','-s -w','-o',str(stage/'app/bin/native-control'),*native_sources],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
m=stage/'manifest';m.write_text('\n'.join('version = '+V if l.split('=',1)[0].strip()=='version' else 'changelog = 授权下载目录选择器；动态 fnOS 权限源和真实 NAS 尚未验收。' if l.split('=',1)[0].strip()=='changelog' else l for l in m.read_text().splitlines() if not l.startswith('checksum'))+'\n')
# Reuse the exact previously retained full corresponding-source material, not a
# fictitious clean checkout. Current application source replaces its old tree.
work=D/'source';work.mkdir()
# keep historical 1.5.1 source material as the locked runtime/input; this is not a clean rebuild
with tarfile.open(REL/'native-1.5.1-source-bundle.tar.gz') as t:
 members=[x for x in t.getmembers() if not x.name.startswith('application-source') and x.name!='SOURCE-MANIFEST.json']
 t.extractall(work,members=members,filter='data')
app=work/'application-source';app.mkdir()
for n in ['src','gateway','native','native-package','tools','docs','dist','public','package.json','package-lock.json','tsconfig.json','index.html','README.md','THIRD_PARTY_NOTICES.md','LICENSE']:
 p=R/n
 if p.is_dir():shutil.copytree(p,app/n,ignore=lambda directory,names:[n for n in names if n=='__pycache__' or (Path(directory)/n).is_socket() or (Path(directory)==R/'native-package' and n=='app')])
 else:shutil.copy2(p,app/n)
materials={str(p.relative_to(work)):sha(p) for p in work.rglob('*') if p.is_file()}
manifest={'version':V,'build_mode':'locked 1.4.8 runtime reused, current UI/gateway compiled locally; NOT clean runtime build','runtime_fpk_sha256':sha(base),'retained_source_sha256':sha(REL/'native-1.4.8-source-bundle.tar.gz'),'files':materials,'nas_authorization_source_verified':False}
(work/'SOURCE-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(source,'w:gz',compresslevel=3) as t:
 for p in work.iterdir():t.add(p,arcname=p.name)
lic=stage/'app/licenses';(lic/'SOURCE-MANIFEST.json').write_text(json.dumps({'version':V,'source_bundle':source.name,'sha256':sha(source),'build_mode':manifest['build_mode']},indent=2)+'\n')
(lic/'LICENSE-SOURCES.md').write_text(f'Complete source material: {source.name}\nSHA256: {sha(source)}\nShip this matching source bundle with the FPK. Local locked-runtime build; NAS authorization, physical phone, and external release acceptance pending.\n')
(lic/'RELEASE-NOTES.md').write_text('1.5.5 单工作区与授权卷/站点分析。仅查询本应用当前动态授权目录；未知权限来源拒绝浏览和路径写入。局部本地验证不代表 NAS ACL 验收。无创建、移动、删除操作。\\n')
build=D/'fnpack';build.mkdir();subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=build,check=True);made=build/'fnos-qbittorrent-native.fpk';assert made.is_file();shutil.copy2(made,out)
for p in [source,out]:p.with_suffix(p.suffix+'.sha256').write_text(sha(p)+'  '+p.name+'\n')
count=0
with tarfile.open(out) as t:
 with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:
  for member in a.getmembers():
   if member.isfile():
    if member.name=='config/resource':
     packaged=json.loads(a.extractfile('config/resource').read());assert packaged==data
    else:assert a.extractfile(member).read()==(stage/'app'/member.name).read_bytes()
    count+=1
 assert next(l for l in t.extractfile('manifest').read().decode().splitlines() if l.startswith('checksum')).split('=',1)[1].strip()==hashlib.md5(t.extractfile('app.tgz').read()).hexdigest()
assert all(sha(Path(p))==h for p,h in prior.items())
resource_audit=audit(out)
report={'resource_audit':resource_audit,'version':V,'fpk':str(out),'fpk_sha256':sha(out),'source':str(source),'source_sha256':sha(source),'package_files_equal_staging':count,'prior_unchanged':True,'build_mode':manifest['build_mode'],'nas_authorization_source_verified':False}
(R/'evidence/workspace156-artifact.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
