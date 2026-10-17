"""Current-source isolated qB/Unix-gateway iframe check; never builds an FPK.
Reuses only the historical runtime and fixture helpers, not historical UI/gateway.
"""
from pathlib import Path
import os, subprocess, re, shutil, uuid
R=Path(__file__).resolve().parents[1]
D=R/'.runtime/five-fixes'/('current-'+getattr(uuid,'uuid4')().hex[:8])
D.mkdir(parents=True,exist_ok=False)
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
for scope in ['public','private']:
 p=D/'app/webui'/scope;shutil.copytree(R/'dist',p)
 for f in p.rglob('*.js'):f.write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
sources=D/'sources';sources.mkdir()
for f in (R/'gateway').glob('*.go'):
 if not f.name.endswith('_test.go'):(sources/f.name).write_text(f.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
(D/'app/bin').mkdir(parents=True)
subprocess.run(['go','build','-trimpath','-o',str(D/'app/bin/gateway'),*map(str,sources.glob('*.go'))],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
# Additive harness copies preserve old release evidence and immutable inputs.
browser=(R/'tools/verify_selection140_browser.mjs').read_text().replace('evidence/selection140-','.runtime/five-fixes/selection-current-')
(D/'browser.mjs').write_text(browser)
s=(R/'tools/verify_selection140_real.py').read_text()
s=s.replace("R=Path(__file__).resolve().parents[1]",'R=Path('+repr(str(R))+')')
s=s.replace(".runtime/selection140",'.runtime/five-fixes/fixture')
s=s.replace("R/('.runtime/package'+version+'/app/webui')",'Path('+repr(str(D/'app/webui'))+')')
s=s.replace("R/('.runtime/package'+version+'/app/bin/gateway')",'Path('+repr(str(D/'app/bin/gateway'))+')')
s=s.replace("'tools/verify_selection140_browser.mjs'",repr(str(D/'browser.mjs')))
s=s.replace('packaged Unix gateway ready','current-source Unix gateway ready (not an FPK)')
s=s.replace("evidence/selection140-real-readback.json",'.runtime/five-fixes/selection-current-readback.json')
exec(compile(s,str(R/'tools/verify_selection140_real.py'),'exec'))
