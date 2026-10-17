"""Material-backed 1.1.4 inventory; inspect shipped bytes, not stale APK DB.
Downloads recipes but never executes them on the host. Does not certify licensing.
"""
from pathlib import Path
import json, hashlib, tarfile, re, shutil, urllib.request, io, concurrent.futures, subprocess
R=Path(__file__).resolve().parents[1]; S=R/'release/native-1.1.4-sources'; T=R/'native-package/app/runtime'
def digest(p, alg='sha256'):return hashlib.new(alg,p.read_bytes()).hexdigest()
def get(url,p):
 p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  with urllib.request.urlopen(url,timeout=120) as r,open(str(p)+'.part','wb') as f:shutil.copyfileobj(r,f)
  Path(str(p)+'.part').rename(p)
 return p
if not S.exists():shutil.copytree(R/'release/native-1.1.3-sources',S)
# Remove inherited assertions and historical package inventories from new evidence.
for n in ['historical-1.1.2','notices']:
 if (S/n).exists():shutil.rmtree(S/n)
owners={};packages={}
for b in (T/'lib/apk/db/installed').read_text().split('\n\n'):
 d={};folder='';last=''
 for line in b.splitlines():
  if ':' not in line:continue
  k,v=line.split(':',1)
  if k=='F':folder=v
  elif k=='R':last=folder+'/'+v;owners[last]={'package':d}
  elif k=='Z' and last:owners[last]['apk_checksum']=v
  elif k not in ['a','M']:d[k]=v
 if d.get('P'):packages[d['P']]=d
# APK installation was interrupted; upgraded files exist with OLD installed DB.
# Bind changed files to downloaded exact APK bytes and APKINDEX metadata instead.
idx={}
for repo in ['main','community']:
 p=get(f'https://dl-cdn.alpinelinux.org/alpine/v3.24/{repo}/x86_64/APKINDEX.tar.gz',S/'build/apk-indexes'/f'{repo}.tar.gz')
 with tarfile.open(p) as tf:text=tf.extractfile('APKINDEX').read().decode()
 for b in text.split('\n\n'):
  d=dict(l.split(':',1) for l in b.splitlines() if ':' in l)
  if 'P' in d:idx[d['P']]={**d,'repo':repo}
overrides={};apk_evidence=[]
for n in ['libssl3','libcrypto3','pcre2','libpcre2-16','zlib','qt6-qttools-dev','patch']:
 d=idx[n];p=get(f'https://dl-cdn.alpinelinux.org/alpine/v3.24/{d["repo"]}/x86_64/{n}-{d["V"]}.apk',S/'build/apks'/f'{n}-{d["V"]}.apk')
 with tarfile.open(p) as tf:
  info=tf.extractfile('.PKGINFO').read().decode()
  assert f'pkgname = {n}\n' in info and f'pkgver = {d["V"]}\n' in info
  for m in tf:
   if not m.isfile() or m.name.startswith('.'):continue
   h=hashlib.sha256(tf.extractfile(m).read()).hexdigest()
   overrides[h]=d
 apk_evidence.append({'package':n,'version':d['V'],'file':str(p.relative_to(S)),'sha256':digest(p),'index_package_checksum':d.get('C'),'metadata':d})
rows=[];used={};mismatches=[]
import base64
for f in sorted(T.rglob('*')):
 if not f.is_file() or f==T/'lib/apk/db/installed':continue
 rel=str(f.relative_to(T));h=digest(f);o=owners.get(rel)
 candidates=[v for k,v in owners.items() if k==rel or k.startswith(rel+'.') or (o and v['package'] is o['package']) or (rel.startswith('lib/ld-musl') and v['package'].get('P')=='musl') or (rel=='etc/ssl/cert.pem' and v['package'].get('P')=='ca-certificates-bundle')]
 # Extracted SONAME symlinks became regular files; compare versioned payload.
 o=next((v for v in candidates if v.get('apk_checksum')=='Q1'+base64.b64encode(hashlib.sha1(f.read_bytes()).digest()).decode()),o)
 d=overrides.get(h) or (o['package'] if o else None)
 if d:
  evidence='downloaded APK payload SHA256' if h in overrides else 'installed APK file SHA1'
  if h not in overrides and o.get('apk_checksum')!='Q1'+base64.b64encode(hashlib.sha1(f.read_bytes()).digest()).decode():mismatches.append(rel)
  used[d['P']]=d
  rows.append({'file':rel,'sha256':h,'package':d['P'],'version':d['V'],'origin':d['o'],'aports_commit':d.get('c'),'license_metadata':d['L'],'ownership_evidence':evidence})
 else:rows.append({'file':rel,'sha256':h,'package':'qBittorrent custom source build' if rel=='usr/bin/qbittorrent-nox' else 'UNRESOLVED'})
assert not mismatches, mismatches
assert not any(x['package']=='UNRESOLVED' for x in rows)
# Update only origins proven changed in shipped bytes.
new_origins={d['o']:d for d in used.values() if d['P'] in ['libssl3','pcre2','zlib']}
for origin,d in new_origins.items():
 p=S/'aports'/origin
 shutil.rmtree(p);p.mkdir()
 recipe=get(f'https://raw.githubusercontent.com/alpinelinux/aports/{d["c"]}/main/{origin}/APKBUILD',p/'APKBUILD').read_text()
 version=re.search(r'^pkgver=(.*)$',recipe,re.M)[1]
 sums=re.search(r'sha512sums=[\"\'](.*?)[\"\']',recipe,re.S)[1]
 for sha,name in re.findall(r'([a-f0-9]{128})\s+(\S+)',sums):
  urls=[f'https://distfiles.alpinelinux.org/edge/{name}', f'https://raw.githubusercontent.com/alpinelinux/aports/{d["c"]}/main/{origin}/{name}']
  if origin=='openssl':urls.append(f'https://github.com/openssl/openssl/releases/download/openssl-{version}/{name}')
  if origin=='pcre2':urls.append(f'https://github.com/PCRE2Project/pcre2/releases/download/pcre2-{version}/{name}')
  if origin=='zlib':urls.append(f'https://zlib.net/fossils/{name}')
  errors=[]
  for u in urls:
   try:
    f=get(u,p/name);assert digest(f,'sha512')==sha;break
   except Exception as e:errors.append(str(e));(p/name).unlink(missing_ok=True)
  else:raise RuntimeError((origin,name,errors))
# Verify every retained recipe input, not only downloads this run.
checks=[]
for p in sorted((S/'aports').glob('*/APKBUILD')):
 text=p.read_text();m=re.search(r'sha512sums=[\"\'](.*?)[\"\']',text,re.S)
 assert m,p
 for sha,name in re.findall(r'([a-f0-9]{128})\s+(\S+)',m[1]):
  f=p.parent/name;ok=f.is_file() and digest(f,'sha512')==sha
  checks.append({'file':str(f.relative_to(S)),'sha512':sha,'verified':ok})
assert all(x['verified'] for x in checks),[x for x in checks if not x['verified']]
notices=[]
archives=list(S.glob('*.tar.gz'))+[p for p in (S/'aports').rglob('*') if p.name.endswith(('.tar.gz','.tar.xz','.tar.bz2','.tgz'))]
for p in archives:
 with tarfile.open(p) as tf:
  for m in tf:
   name=Path(m.name).name.lower();parts=Path(m.name).parts
   # Include Qt attribution manifests and REUSE license directory, not just top-level COPYING.
   if m.isfile() and m.size<3000000 and (re.match(r'^(copying|copyright|licen[cs]e|notice|authors)([._-]|$)',name) or name=='qt_attribution.json' or 'LICENSES' in parts):
    assert not Path(m.name).is_absolute() and '..' not in parts
    data=tf.extractfile(m).read();out=S/'notices'/p.name/m.name;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data)
    notices.append({'archive':str(p.relative_to(S)),'member':m.name,'file':str(out.relative_to(S)),'sha256':hashlib.sha256(data).hexdigest()})
(S/'runtime-inventory.json').write_text(json.dumps(rows,indent=2))
(S/'actual-packages.json').write_text(json.dumps(list(used.values()),indent=2))
(S/'build/apk-acquisition.json').write_text(json.dumps(apk_evidence,indent=2))
(S/'source-verification.json').write_text(json.dumps(checks,indent=2))
(S/'notice-index.json').write_text(json.dumps(notices,indent=2))
(S/'SBOM.json').write_text(json.dumps({'format':'project per-file inventory, not SPDX certification','version':'1.1.4','files':rows,'components':list(used.values()),'static_components':{'qBittorrent':'5.2.4','libtorrent':'c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9','Boost':'1.86.0','Go':'go1.23.6'},'old_apk_database_is_stale':True},indent=2))
print(json.dumps({'runtime_files':len(rows),'runtime_packages':len(used),'recipe_inputs_verified':len(checks),'notice_members':len(notices),'new_apks':apk_evidence},indent=2))
