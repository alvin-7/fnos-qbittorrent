#!/usr/bin/env python3
"""Fetch hash-locked partial source inputs only, never execute/extract recipes."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]

def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / '.runtime' / 'native-input-cache')
    parser.add_argument('--verify-only', action='store_true')
    args = parser.parse_args()
    lock = json.loads((ROOT / 'docs' / 'NATIVE_INPUTS.lock.json').read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    for entry in lock['source_inputs']:
        target = args.cache / entry['file']
        if not target.exists():
            if args.verify_only:
                raise SystemExit('BLOCKED missing cached input: ' + entry['file'])
            temporary = target.with_suffix(target.suffix + '.partial')
            if temporary.exists():
                raise SystemExit('Refusing existing partial download: ' + str(temporary))
            with urllib.request.urlopen(entry['url'], timeout=90) as source, temporary.open('xb') as output:
                while chunk := source.read(1024 * 1024):
                    output.write(chunk)
            actual = sha256(temporary)
            if actual != entry['sha256']:
                raise SystemExit('BLOCKED download hash mismatch; retained .partial: ' + entry['file'])
            temporary.rename(target)
        actual = sha256(target)
        if actual != entry['sha256']:
            raise SystemExit('BLOCKED cache hash mismatch: ' + entry['file'])
        print('VERIFIED', entry['file'], actual, entry['license'])
    print('Partial source inputs verified; full native runtime/FPK build remains BLOCKED.')

if __name__ == '__main__':
    main()
