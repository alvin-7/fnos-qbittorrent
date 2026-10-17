"""Build immutable 1.2.6 from the untouched 1.2.5 FPK; never overwrite prior artifacts."""
from pathlib import Path
import hashlib, io, json, os, shutil, subprocess, tarfile
R = Path(__file__).resolve().parents[1]
base = R / 'release/fnos-qbittorrent-native-1.2.5-x86_64.fpk'
out = R / 'release/fnos-qbittorrent-native-1.2.6-x86_64.fpk'
stage = R / '.runtime/package126'
overlay = R / 'release/native-1.2.6-share-ratio-source-overlay.tar.gz'
assert base.is_file() and out == R / 'release/fnos-qbittorrent-native-1.2.6-x86_64.fpk'
assert not out.exists() and not stage.exists() and not overlay.exists()
stage.mkdir(parents=True)
with tarfile.open(base) as t:
    t.extractall(stage, filter='data')
with tarfile.open(fileobj=io.BytesIO((stage/'app.tgz').read_bytes())) as t:
    t.extractall(stage/'app', filter='data')
(stage/'app.tgz').unlink()
manifest = stage/'manifest'
manifest.write_text('\n'.join(x.replace('version               = 1.2.5', 'version               = 1.2.6') for x in manifest.read_text().splitlines())+'\n')
subprocess.run(['npm','run','build'], cwd=R, env=dict(os.environ, VITE_NATIVE='1'), check=True)
for scope in ('public','private'):
    p = stage/'app/webui'/scope
    shutil.rmtree(p)
    shutil.copytree(R/'dist', p)
    for f in p.rglob('*.js'):
        f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(stage)], cwd=R, check=True)
assert (R/'fnos-qbittorrent-native.fpk').is_file()
shutil.copyfile(R/'fnos-qbittorrent-native.fpk', out)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
(out.with_suffix('.fpk.sha256')).write_text(sha(out)+'  '+out.name+'\n')
files = ['src/Settings.tsx','src/pt.ts','src/Detail.tsx','tests/share-ratio.spec.ts','native/control.go','native/control_test.go','native/port_test.go','gateway/diagnostics.go','gateway/native.go']
with tarfile.open(overlay, 'w:gz') as t:
    for rel in files:
        t.add(R/rel, arcname=rel)
(overlay.with_suffix('.tar.gz.sha256')).write_text(sha(overlay)+'  '+overlay.name+'\n')
report = {'version':'1.2.6','base':'release/fnos-qbittorrent-native-1.2.5-x86_64.fpk','fpk_sha256':sha(out),'overlay_sha256':sha(overlay),'bytes':out.stat().st_size,'base_untouched':sha(base)=='14b04dfc42ba2396bbab8a64b4abea770fc055a3688ff7191403253b980c5bce','stage':str(stage.relative_to(R)),'nas_verified':False,'passed':True}
(R/'evidence/native-package-audit-1.2.6.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
print(json.dumps(report, indent=2, ensure_ascii=False))
