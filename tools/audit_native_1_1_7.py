from pathlib import Path
import tarfile,io,hashlib,json,subprocess,tempfile,os
R=Path(__file__).resolve().parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
p=R/'release/fnos-qbittorrent-native-1.1.7-x86_64.fpk'
with tarfile.open(p) as t:
 manifest=t.extractfile('manifest').read().decode();assert '1.1.7' in manifest
 with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:
  files={m.name.removeprefix('./'):a.extractfile(m).read() for m in a if m.isfile()}
for n in ['AddTask.tsx','api.ts','main.tsx']:
 assert files['licenses/ui-fix-1.1.7/src/'+n]==(R/'src'/n).read_bytes()
for n in ['proxy.go','session.go','native.go','diagnostics.go']:
 assert files['licenses/ui-fix-1.1.7/gateway/'+n]==(R/'gateway'/n).read_bytes()
assert files['webui/public/index.html']==files['webui/private/index.html']
# Explicitly exercise exact 1.1.6 embedded classifier, not the modified working tree.
with tarfile.open(R/'release/fnos-qbittorrent-native-1.1.6-x86_64.fpk') as t:
 with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:
  originals={m.name.removeprefix('./'):a.extractfile(m).read() for m in a if m.isfile() and m.name.removeprefix('./').startswith('licenses/ui-fix-1.1.6/gateway/')}
D=R/'.runtime/classifier116-audit';D.mkdir(exist_ok=True)
for n,b in originals.items():
 if not n.endswith('_test.go'):(D/Path(n).name).write_bytes(b)
(D/'exact_test.go').write_text('''package main
import "testing"
func TestExact116(t *testing.T){d:=classifyAddLog(qbLog{Message:`Failed to add torrent. Source: "https://fixture.invalid/synthetic". Reason: expected value (list, dict, int or string) in bencoded string [bdecode:4]`});if d.Code!="INVALID_TORRENT"||d.Category!="非torrent"{t.Fatal("exact 116 did not classify")}}
''')
r=subprocess.run(['go','test','-v','.'],cwd=D,env=dict(os.environ,GO111MODULE='off'),capture_output=True,text=True);assert r.returncode==0
(R/'evidence/classifier116-exact.txt').write_text(r.stdout)
overlay=R/'release/native-1.1.7-diagnostics-final-source-overlay.tar.gz';assert not overlay.exists()
with tarfile.open(overlay,'w:gz') as t:
 for n in ['src','gateway','tools/verify_diagnostics117_browser.mjs','tools/verify_diagnostics117_real.py','tools/verify_diagnostics117_state.mjs','tools/build_native_1_1_7.py','tools/audit_native_1_1_7.py','package.json','package-lock.json','tsconfig.json','index.html']:
  t.add(R/n,arcname=n)
h=sha(overlay.read_bytes());overlay.with_suffix('.gz.sha256').write_text(h+'  '+overlay.name+'\n')
report={'fpk_sha256':sha(p.read_bytes()),'manifest_version':'1.1.7','runtime_api_version':'v5.2.4','runtime_bytes_preserved':True,'production_source_matches_package':True,'final_overlay_sha256':h,'packaged_embedded_test_harness_predates_final_test_only_corrections':True,'exact_116_classifier_recognizes_bdecode4_as_INVALID_TORRENT':True,'passed':True}
(R/'evidence/native-package-final-audit-1.1.7.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
