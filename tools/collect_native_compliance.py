"""Inventory actual native runtime, pin acquisition recipes, retain source/licenses.
This is an evidence collector, NOT a declaration of GPL/LGPL compliance.
"""
from pathlib import Path
import json,hashlib,urllib.request,concurrent.futures,re,tarfile,subprocess
R=Path(__file__).resolve().parents[1];T=R/'native-package/app';L=T/'licenses';S=R/'release/native-1.1.1-sources';S.mkdir(exist_ok=True)
packages=[];owners={}
for block in (T/'runtime/lib/apk/db/installed').read_text().split('\n\n'):
 d={};folder=''
 for line in block.splitlines():
  if ':' not in line:continue
  k,v=line.split(':',1)
  if k=='F':folder=v
  elif k=='R':owners[folder+'/'+v]=d
  elif k not in ['Z','a','M']:d[k]=v
 if d:packages.append(d)
rows=[]; used={}
for f in sorted((T/'runtime').rglob('*')):
 if not f.is_file():continue
 rel=str(f.relative_to(T/'runtime'));d=owners.get(rel)
 if rel=='lib/apk/db/installed':continue
 if not d:
  # Extracted libraries use SONAME aliases; map to APK's versioned filename.
  candidates=[v for k,v in owners.items() if k.startswith(rel+'.') or (rel.startswith('lib/ld-musl') and v.get('P')=='musl')]
  if candidates:d=candidates[0]
 row={'file':rel,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
 if d:
  row.update(package=d['P'],version=d['V'],license=d['L'],origin=d.get('o'),aports_commit=d.get('c'));used[d['P']]=d
 else:row['package']='qBittorrent (upstream custom build)' if rel=='usr/bin/qbittorrent-nox' else 'UNRESOLVED'
 rows.append(row)

def fetch(item):
 name,url=item;p=S/name;p.parent.mkdir(parents=True,exist_ok=True)
 try:
  if not p.exists():
   with urllib.request.urlopen(url,timeout=45) as res:p.write_bytes(res.read())
  return {'file':name,'url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
 except Exception as e:return {'file':name,'url':url,'error':str(e)}
urls=[]
for d in used.values():
 origin=d.get('o',d['P']);commit=d.get('c','')
 # Aports origin directory can be in main/community/testing: try all, retain only real recipe.
 for repo in ['main','community','testing']:urls.append((f'aports/{d["P"]}/{repo}-APKBUILD',f'https://raw.githubusercontent.com/alpinelinux/aports/{commit}/{repo}/{origin}/APKBUILD'))
license_ids=set()
for d in used.values():license_ids.update(re.findall(r'[A-Za-z0-9][A-Za-z0-9.\-+]*',d['L']))
for ident in sorted(license_ids-{'AND','OR','WITH','Public-Domain'}):urls.append((f'licenses/{ident}.txt',f'https://raw.githubusercontent.com/spdx/license-list-data/main/text/{ident}.txt'))
urls += [('qBittorrent-release-5.2.4.tar.gz','https://codeload.github.com/qbittorrent/qBittorrent/tar.gz/refs/tags/release-5.2.4'),('libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9.tar.gz','https://codeload.github.com/arvidn/libtorrent/tar.gz/c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9'),('licenses/Boost-1.0.txt','https://raw.githubusercontent.com/boostorg/boost/boost-1.86.0/LICENSE_1_0.txt'),('image-build-99a2044d7f4f7d36da559cbc6439934a80502967.tar.gz','https://codeload.github.com/qbittorrent/docker-qbittorrent-nox/tar.gz/99a2044d7f4f7d36da559cbc6439934a80502967')]
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:results=list(ex.map(fetch,urls))
shipped=[]
for d in used.values():
 recipes=[x for x in results if x['file'].startswith('aports/'+d['P']+'/') and 'sha256' in x]
 shipped.append({'package':d['P'],'version':d['V'],'license':d['L'],'source_origin':d.get('o'),'aports_commit':d.get('c'),'recipes':recipes,'corresponding_source_retained':False})
# Actual Go runtime license, plus the precise application build sources (no private state).
go=Path(subprocess.check_output(['go','env','GOROOT']).decode().strip());(S/'licenses/Go-LICENSE').write_bytes((go/'LICENSE').read_bytes())
with tarfile.open(S/'application-build-source.tar.gz','w:gz') as tf:
 for name in ['native','gateway','src','tools','package.json','package-lock.json','tsconfig.json','index.html']:
  p=R/name
  for f in ([p] if p.is_file() else p.rglob('*')):
   if f.is_file() and '__pycache__' not in str(f) and f.name!='fnpack':tf.add(f,arcname=str(f.relative_to(R)))
report={'distributable':False,'status':'不宜分发 / DO NOT DISTRIBUTE','runtime_files':rows,'packages':shipped,'static_components':[{'name':'qBittorrent','version':'5.2.4'},{'name':'libtorrent-rasterbar','commit':'c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9'},{'name':'Boost','version':'1.86.0'},{'name':'Go runtime','version':subprocess.check_output(['go','version']).decode().strip()}], 'acquisitions':results,'blockers':['Exact Alpine corresponding upstream archives, aports patches and complete copyright/license notices have not all been retained. Recipe plus source URL is NOT corresponding source delivery.','Qt LGPL source/relink/replace requirements and GPL complete corresponding build inputs remain unverified.','Boost exact source and Go toolchain corresponding source not retained; static-component closure not independently reproducibly rebuilt.','No written source offer is made. No public binary distribution permitted until the above is closed.']}
(L/'NATIVE-COMPLIANCE.json').write_text(json.dumps(report,indent=2));(R/'evidence/native-compliance-1.1.1.json').write_text(json.dumps(report,indent=2))
for p in (S/'licenses').glob('*'): (L/p.name).write_bytes(p.read_bytes())
(L/'DO-NOT-DISTRIBUTE.txt').write_text('不宜分发。仅本地隔离测试。GPL/LGPL对应源码与逐组件版权声明未齐；源码链接、SPDX许可证或官方镜像来源不能替代发行义务。详见 NATIVE-COMPLIANCE.json 和随包 source acquisition 清单。\n')
(L/'NATIVE-SOURCES.md').write_text('# Native 1.1.1: NOT DISTRIBUTABLE\nSee NATIVE-COMPLIANCE.json for per-file ownership/hash, exact APK version/origin/aports commit and source recipes. Local retained source: release/native-1.1.1-sources/. qB release-5.2.4, libtorrent c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9, Boost 1.86.0; Go version recorded in inventory. Source archives/recipes/license texts collected are partial, NOT full corresponding source. Qt and all LGPL/GPL build inputs, patches, copyright notices, relinking and replacement must be completed before distribution. No written offer has been issued.\n')
print(json.dumps({'runtime_files':len(rows),'apk_components':len(used),'downloaded':sum('sha256' in x for x in results),'failed_probes':sum('error' in x for x in results),'distributable':False}))
