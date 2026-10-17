#!/usr/bin/env python3
"""Read-only candidate inventory; no git init, no secret values in reports.

Supports this repository's simple .gitignore patterns (not a general Git matcher).
Actual staged files must be rescanned before publication; forced/tracked ignored
files are outside this pre-initialization inventory.
"""
from pathlib import Path
import fnmatch
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
RULES = [s.strip() for s in (ROOT / '.gitignore').read_text().splitlines()
         if s.strip() and not s.startswith('#')]

def ignored(path):
    rel = path.as_posix()
    result = False
    for raw in RULES:
        negate = raw.startswith('!')
        rule = raw[1:] if negate else raw
        anchored = rule.startswith('/')
        rule = rule.lstrip('/')
        directory = rule.endswith('/')
        rule = rule.rstrip('/')
        candidates = [rel] if anchored or '/' in rule else path.parts
        if directory:
            match = (rel == rule or rel.startswith(rule + '/')) if anchored or '/' in rule else rule in path.parts
        else:
            match = any(fnmatch.fnmatchcase(s, rule) for s in candidates)
        if match:
            result = not negate
    return result

PATTERNS = {
    'personal_absolute_path': r'/(?:home|Users)/[^/\s]+/',
    'private_ipv4_review': r'\b(?:192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)\b',
    'signed_url_review': r'https?://[^\s"<>]+[?&](?:passkey|token|authkey|sign|signature|key)=',
    'credential_literal_review': r'''(?i)(?:password|passwd|secret|token|api_key)\s*[:=]\s*['"][^'"\n]{6,}['"]''',
    'private_key_or_provider_token': r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}',
    'redacted_placeholder_review': r'\{\{(?:PASSWORD|SECRET|TOKEN|EMAIL)_[^}]+\}\}',
    'unsafe_exec_review': r'os\.system\(|shell\s*=\s*True|\beval\(|\bexec\(',
}

def main():
    files, findings, symlinks = [], [], []
    # Prune ignored trees, rather than loading private runtime or archived sources.
    import os
    for base, dirs, names in os.walk(ROOT, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d != '.git' and not ignored((Path(base)/d).relative_to(ROOT)))
        for name in sorted(names):
            p = Path(base)/name
            rel = p.relative_to(ROOT)
            if ignored(rel):
                continue
            if p.is_symlink():
                symlinks.append(str(rel))
                continue
            data = p.read_bytes()
            files.append({'path': str(rel), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
            if len(data) > 5 * 1024 * 1024:
                findings.append({'path': str(rel), 'category': 'large_file_over_5MiB'})
            if b'\x00' in data:
                continue
            for line, text in enumerate(data.decode('utf-8', errors='replace').splitlines(), 1):
                for category, pattern in PATTERNS.items():
                    if re.search(pattern, text):
                        findings.append({'path': str(rel), 'line': line, 'category': category})
    report = {'scope': 'pre-git source candidates, simple ignore rules; findings are review flags, not proven secrets',
              'file_count': len(files), 'total_bytes': sum(x['bytes'] for x in files),
              'files': sorted(files, key=lambda x:x['path']), 'findings': findings,
              'symlinks_not_uploaded': symlinks}
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
