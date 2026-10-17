"""Read-only immutable artifact audit, then isolated final-byte regression.

Requires local release/staging inputs; never targets NAS or inherited tasks.
Writes only new version-specific verification/evidence paths, refuses reruns.
"""
from pathlib import Path
import hashlib
import io
import json
import os
import subprocess
import tarfile

R = Path(__file__).resolve().parents[1]
D = R / '.runtime/strip148-verification-v2'
assert not D.exists(), 'immutable verification already exists'
D.mkdir()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
old = json.loads((R / '.runtime/strip148-prior-hashes.json').read_text())
assert all(sha(R / p) == digest for p, digest in old.items()), 'historical artifact changed'
fpk = R / 'release/fnos-qbittorrent-native-1.4.8-x86_64.fpk'
stage = R / '.runtime/package148'
count = 0
with tarfile.open(fpk) as outer:
    with tarfile.open(fileobj=io.BytesIO(outer.extractfile('app.tgz').read())) as app:
        for member in app.getmembers():
            if member.isfile():
                target = stage / 'app' / member.name
                assert target.is_file(), member.name
                assert app.extractfile(member).read() == target.read_bytes(), member.name
                assert not any(s in Path(member.name).parts for s in ['node_modules', '.runtime']), member.name
                count += 1
    manifest = outer.extractfile('manifest').read().decode()
    checksum_line = next(line for line in manifest.splitlines() if line.startswith('checksum'))
    assert checksum_line.split('=', 1)[1].strip() == hashlib.md5(outer.extractfile('app.tgz').read()).hexdigest()
    assert '\n'.join(line for line in manifest.splitlines() if not line.startswith('checksum')) == (stage / 'manifest').read_text().rstrip('\n')
# Exact current native UI transformation, not merely a historical bundle comparison.
for scope in ['public', 'private']:
    for source in (R / 'dist').rglob('*'):
        if source.is_file():
            data = source.read_bytes()
            if source.suffix == '.js':
                data = data.replace(b'/app/fnos-qbittorrent', b'/app/fnos-qbittorrent-native')
            assert (stage / 'app/webui' / scope / source.relative_to(R / 'dist')).read_bytes() == data
for source in (R / 'gateway').glob('*.go'):
    if not source.name.endswith('_test.go'):
        assert (R / '.runtime/gateway148-native' / source.name).read_text() == source.read_text().replace('/app/fnos-qbittorrent', '/app/fnos-qbittorrent-native')
strip = json.loads((R / 'evidence/strip-1.4.8.json').read_text())
for item in strip:
    binary = stage / item['path']
    assert sha(binary) == item['after_sha256']
    assert '.debug_info' not in subprocess.check_output(['readelf', '-SW', str(binary)], text=True)
source_bundle = R / 'release/native-1.4.8-source-bundle.tar.gz'
assert json.loads((stage / 'app/licenses/SOURCE-MANIFEST.json').read_text())['sha256'] == sha(source_bundle)
report = dict(version='1.4.8', fpk_sha256=sha(fpk), source_sha256=sha(source_bundle),
              packaged_regular_files_equal_staging=count, prior_artifacts_unchanged=True,
              current_native_ui_equal=True, current_gateway_source_equal=True,
              binaries=strip, sizes={p.name: p.stat().st_size for p in [R / 'release/fnos-qbittorrent-native-1.4.7-x86_64.fpk', fpk]},
              rss_reduction_claimed=False, nas_verified=False)
(R / 'evidence/strip148-artifact-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASS artifact/staging/current UI/current gateway/historical hashes/source binding', flush=True)
# Preserve original harnesses and all historical evidence. Only additive test copies.
regression = (R / 'tools/verify_regression140.py').read_text().replace('140', '148')
regression = regression.replace('R=Path(__file__).resolve().parents[1]', 'R=Path(' + repr(str(R)) + ')')
regression_path = D / 'regression148.py'
regression_path.write_text(regression)
subprocess.run(['python3', str(regression_path)], cwd=R, check=True)
selection = (R / 'tools/verify_selection140_real.py').read_text()
selection = selection.replace('R=Path(__file__).resolve().parents[1]', 'R=Path(' + repr(str(R)) + ')')
selection = selection.replace('.runtime/selection140', '.runtime/selection148').replace('evidence/selection140', 'evidence/selection148')
selection = selection.replace("'tools/verify_selection140_browser.mjs'", repr(str(D / 'selection148.mjs')))
browser = (R / 'tools/verify_selection140_browser.mjs').read_text().replace('evidence/selection140', 'evidence/selection148')
(D / 'selection148.mjs').write_text(browser)
(D / 'selection148.py').write_text(selection)
subprocess.run(['python3', str(D / 'selection148.py')], cwd=R, env=dict(os.environ, SELECTION_PACKAGE='148'), check=True)
print('PASS final package PT/transfer/scheduler/diagnostics/desktop+mobile iframe/selection regressions')
