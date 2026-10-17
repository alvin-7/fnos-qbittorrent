#!/usr/bin/env python3
"""Build original application from source only; not a native runtime/FPK build."""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / '.runtime' / 'checkout-build'
    out.mkdir(parents=True, exist_ok=False)  # Never overwrite evidence or a release.
    subprocess.run(['npm', 'ci', '--registry=https://registry.npmjs.org'], cwd=ROOT, check=True)
    subprocess.run(['npm', 'run', 'build'], cwd=ROOT, env=dict(os.environ, VITE_NATIVE='1'), check=True)
    for scope in ('public', 'private'):
        dest = out / 'app' / 'webui' / scope
        shutil.copytree(ROOT / 'dist', dest)
        for file in dest.rglob('*.js'):
            file.write_text(file.read_text().replace('/app/fnos-qbittorrent', '/app/fnos-qbittorrent-native'))
    sources = out / 'gateway-source'
    sources.mkdir()
    for file in sorted((ROOT / 'gateway').glob('*.go')):
        if not file.name.endswith('_test.go'):
            (sources / file.name).write_text(file.read_text().replace('/app/fnos-qbittorrent', '/app/fnos-qbittorrent-native'))
    binaries = out / 'app' / 'bin'
    binaries.mkdir(parents=True)
    env = dict(os.environ, GO111MODULE='off', CGO_ENABLED='0', GOOS='linux', GOARCH='amd64')
    subprocess.run(['go', 'build', '-trimpath', '-o', str(binaries / 'gateway'), *map(str, sorted(sources.glob('*.go')))], cwd=ROOT, env=env, check=True)
    subprocess.run(['go', 'build', '-trimpath', '-o', str(binaries / 'native-control'), str(ROOT / 'native' / 'control.go')], cwd=ROOT, env=env, check=True)
    subprocess.run(['go', 'test', '-race', './gateway', './native'], cwd=ROOT, env=dict(os.environ, GO111MODULE='off'), check=True)
    subprocess.run(['go', 'vet', './gateway', './native'], cwd=ROOT, env=dict(os.environ, GO111MODULE='off'), check=True)
    for name in ('selection140', 'label_batch130', 'labels130', 'connector134_validation', 'pt119', 'five_fixes'):
        subprocess.run(['node', f'tools/test_{name}.mjs'], cwd=ROOT, check=True)
    print('PASS original application source build/tests; NOT a native runtime, complete corresponding source, or FPK build:', out)

if __name__ == '__main__':
    main()
