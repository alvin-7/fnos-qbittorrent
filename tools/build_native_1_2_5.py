"""UI/brand-only immutable release; preserve ALL backend/runtime bytes."""
from pathlib import Path
import hashlib,io,json,os,shutil,subprocess,tarfile,struct
R=Path(__file__).resolve().parents[1]
old=R/'release/fnos-qbittorrent-native-1.2.3-x86_64.fpk';out=R/'release/fnos-qbittorrent-native-1.2.5-x86_64.fpk';stage=R/'.runtime/package125'
assert old.is_file() and not out.exists() and not stage.exists()
stage.mkdir()
with tarfile.open(old) as t:
 t.extractall(stage,filter='data')
 with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:a.extractall(stage/'app',filter='data')
(stage/'app.tgz').unlink()
p=stage/'manifest';p.write_text('\n'.join(x.replace('1.2.3','1.2.5').replace('轻下载 · qB Native 测试','飞牛 PT 下载') for x in p.read_text().splitlines() if not x.startswith('checksum'))+'\n')
p=stage/'app/ui/config';config=json.loads(p.read_text());entry=config['.url']['fnos-qbittorrent-native.main'];entry['title']='飞牛 PT 下载';assert entry['gatewayPrefix']=='/app/fnos-qbittorrent-native';p.write_text(json.dumps(config,ensure_ascii=False))
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ['public','private']:
 p=stage/'app/webui'/scope;shutil.rmtree(p);shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
# PNG assets are genuinely rendered from the original SVG using Chromium.
subprocess.run(['node',str(R/'tools/render_icon124.mjs'),str(stage)],cwd=R,check=True)
(R/'fnos-qbittorrent-native.fpk').unlink(missing_ok=True)
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)],cwd=R,check=True)
assert (R/'fnos-qbittorrent-native.fpk').is_file();shutil.copyfile(R/'fnos-qbittorrent-native.fpk',out)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out.with_suffix('.fpk.sha256').write_text(sha(out)+'  '+out.name+'\n')
with tarfile.open(old) as ot,tarfile.open(out) as nt:
 with tarfile.open(fileobj=io.BytesIO(ot.extractfile('app.tgz').read())) as oa,tarfile.open(fileobj=io.BytesIO(nt.extractfile('app.tgz').read())) as na:
  previous={m.name.removeprefix('./'):oa.extractfile(m).read() for m in oa if m.isfile()};new={m.name.removeprefix('./'):na.extractfile(m).read() for m in na if m.isfile()}
  changed=[n for n,b in previous.items() if new.get(n)!=b]
  assert all(n.startswith('webui/') or n=='ui/config' or n.startswith('ui/images/') for n in changed),changed
  assert all(b==(stage/'app'/n).read_bytes() for n,b in new.items())
report={'version':'1.2.5','sha256':sha(out),'bytes':out.stat().st_size,'backend_runtime_unchanged':True,'changed_previous_files':changed,'icons':{},'passed':True}
for path,size in [('ICON.PNG',64),('ICON_256.PNG',256),('app/ui/images/icon_64.png',64),('app/ui/images/icon_256.png',256)]:
 p=stage/path;assert struct.unpack('>II',p.read_bytes()[16:24])==(size,size);report['icons'][path]={'width':size,'height':size,'sha256':sha(p)}
(R/'evidence/native-package-audit-1.2.5.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='changed_previous_files'},indent=2))
