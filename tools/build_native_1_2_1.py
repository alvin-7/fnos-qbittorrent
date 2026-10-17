"""Build immutable native 1.2.1 from native 1.2.0; never overwrite prior artifacts."""
from pathlib import Path
import hashlib, io, json, os, shutil, subprocess, tarfile
R=Path(__file__).resolve().parents[1]
old=R/'release/fnos-qbittorrent-native-1.2.0-x86_64.fpk'
out=R/'release/fnos-qbittorrent-native-1.2.1-x86_64.fpk'
stage=R/'.runtime/package121'
assert old.is_file(), old
assert not out.exists(), 'immutable output exists; choose next version'
assert not stage.exists(), 'staging exists; remove only after inspecting it'
stage.mkdir(parents=True)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
with tarfile.open(old) as t:
    t.extractall(stage, filter='data')
    with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:
        a.extractall(stage/'app', filter='data')
(stage/'app.tgz').unlink()
manifest=stage/'manifest'
manifest.write_text('\n'.join(x.replace('1.2.0','1.2.1') for x in manifest.read_text().splitlines() if not x.startswith('checksum'))+'\n')
subprocess.run(['npm','run','build'], cwd=R, env=dict(os.environ, VITE_NATIVE='1'), check=True)
for scope in ['public','private']:
    p=stage/'app/webui'/scope; shutil.rmtree(p); shutil.copytree(R/'dist', p)
    for f in p.rglob('*.js'):
        f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
sources=R/'.runtime/gateway121'
if sources.exists(): shutil.rmtree(sources)
sources.mkdir()
for f in (R/'gateway').glob('*.go'):
    if not f.name.endswith('_test.go'):
        (sources/f.name).write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
subprocess.run(['go','build','-trimpath','-o',str(stage/'app/bin/gateway'),*map(str,sources.glob('*.go'))], env=dict(os.environ, GO111MODULE='off', CGO_ENABLED='0'), check=True)
(stage/'app/app.sock').unlink(missing_ok=True); (R/'fnos-qbittorrent-native.fpk').unlink(missing_ok=True)
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)], cwd=R, check=True)
assert (R/'fnos-qbittorrent-native.fpk').is_file(); shutil.copyfile(R/'fnos-qbittorrent-native.fpk', out)
(out.with_suffix('.fpk.sha256')).write_text(sha(out)+'  '+out.name+'\n')
files={}; preserved=0
with tarfile.open(old) as ot, tarfile.open(out) as nt:
    with tarfile.open(fileobj=io.BytesIO(ot.extractfile('app.tgz').read())) as oa, tarfile.open(fileobj=io.BytesIO(nt.extractfile('app.tgz').read())) as na:
        new={m.name.removeprefix('./'):na.extractfile(m).read() for m in na if m.isfile()}
        for m in oa:
            if m.isfile():
                n=m.name.removeprefix('./')
                if not n.startswith('webui/') and n!='bin/gateway': assert new[n]==oa.extractfile(m).read(), n; preserved+=1
        for n,b in new.items(): assert b==(stage/'app'/n).read_bytes(), n; files[n]=hashlib.sha256(b).hexdigest()
report={'version':'1.2.1','sha256':sha(out),'bytes':out.stat().st_size,'all_previous_non_ui_files_preserved':preserved,'files':files,'passed':True}
(R/'evidence/native-package-audit-1.2.1.json').write_text(json.dumps(report, indent=2))
overlay=R/'release/native-1.2.1-session-source-overlay.tar.gz'; assert not overlay.exists()
with tarfile.open(overlay,'w:gz') as t:
    for n in ['src/api.ts','gateway','tools/verify_session_rebuild.mjs','tools/build_native_1_2_1.py','docs/native-1.2.0.md','package.json','package-lock.json','tsconfig.json','index.html']: t.add(R/n, arcname=n)
(overlay.with_suffix('.gz.sha256')).write_text(sha(overlay)+'  '+overlay.name+'\n')
print(json.dumps({'version':'1.2.1','fpk_sha256':sha(out),'overlay_sha256':sha(overlay),'preserved':preserved,'passed':True}, indent=2))
