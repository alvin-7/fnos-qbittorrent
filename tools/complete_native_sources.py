"""Retain checksum-verified Alpine distfiles and exact local recipe inputs.
Never executes downloaded recipes. Failures remain individual release gates.
"""
import pathlib,json,re,hashlib,urllib.request,concurrent.futures,shutil,tarfile,subprocess
R=pathlib.Path(__file__).resolve().parents[1]; S=R/'release/native-1.1.2-sources';S.mkdir(exist_ok=True)
old=json.loads((R/'evidence/native-compliance-1.1.1.json').read_text())
def get(url,p):
 p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  tmp=p.with_name(p.name+'.part')
  with urllib.request.urlopen(url,timeout=120) as r,open(tmp,'wb') as f:shutil.copyfileobj(r,f)
  tmp.rename(p)
 return p
jobs=[];origins={}
for d in old['packages']:
 key=(d['source_origin'],d['aports_commit'])
 if key in origins:continue
 recipe=d['recipes'][0];txt=(R/'release/native-1.1.1-sources'/recipe['file']).read_text();repo=recipe['file'].split('/')[-1].split('-')[0]
 folder=S/'aports'/d['source_origin'];folder.mkdir(parents=True,exist_ok=True);(folder/'APKBUILD').write_text(txt)
 sums=re.search(r'sha512sums=[\"\'](.*?)[\"\']',txt,re.S)
 entries=[] if not sums else re.findall(r'([a-f0-9]{128})\s+(\S+)',sums[1])
 origins[key]={'origin':key[0],'commit':key[1],'packages':[x['package'] for x in old['packages'] if (x['source_origin'],x['aports_commit'])==key],'recipe_sha256':hashlib.sha256(txt.encode()).hexdigest(),'expected_files':len(entries)}
 for digest,name in entries:
  jobs.append((key,name,digest,[f'https://distfiles.alpinelinux.org/edge/{name}',f'https://raw.githubusercontent.com/alpinelinux/aports/{key[1]}/{repo}/{key[0]}/{name}']))
def acquire(job):
 key,name,digest,urls=job;p=S/'aports'/key[0]/name;errors=[]
 for url in urls:
  try:
   get(url,p);actual=hashlib.sha512(p.read_bytes()).hexdigest()
   if actual!=digest:p.unlink();raise ValueError('SHA512 mismatch')
   row={'origin':key[0],'file':str(p.relative_to(S)),'url':url,'sha512':digest,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'verified':True};print('OK',row['file'],flush=True);return row
  except Exception as e:errors.append(str(e))
 print('FAIL',key[0],name,flush=True);return {'origin':key[0],'file':str(p.relative_to(S)),'verified':False,'errors':errors,'expected_sha512':digest,'urls':urls}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:results=list(pool.map(acquire,jobs))
(S/'alpine-acquisition.json').write_text(json.dumps({'origins':list(origins.values()),'files':results},indent=2))
# Retain already acquired original sources without modifying the old release.
for name in ['qBittorrent-release-5.2.4.tar.gz','libtorrent-c5ff6c3186a92ddec01f6f0a8146aaedb4a1c3f9.tar.gz','image-build-99a2044d7f4f7d36da559cbc6439934a80502967.tar.gz']:
 shutil.copyfile(R/'release/native-1.1.1-sources'/name,S/name)
extra=[]
for name,url in [('boost_1_86_0.tar.gz','https://archives.boost.io/release/1.86.0/source/boost_1_86_0.tar.gz'),(subprocess.check_output(['go','env','GOVERSION']).decode().strip()+'.src.tar.gz','https://go.dev/dl/'+subprocess.check_output(['go','env','GOVERSION']).decode().strip()+'.src.tar.gz')]:
 try:
  p=get(url,S/name);extra.append({'file':name,'url':url,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
 except Exception as e:extra.append({'file':name,'url':url,'error':str(e)})
(S/'extra-acquisition.json').write_text(json.dumps(extra,indent=2))
# Retain copyright/license files verbatim, including embedded components.
notices=[]
archives=list(S.glob('*.tar.gz'))+[S/x['file'] for x in results if x['verified'] and any(x['file'].endswith(ext) for ext in ['.tar.gz','.tar.xz','.tar.bz2','.tgz'])]
for p in archives:
 try:
  with tarfile.open(p) as tf:
   for m in tf:
    base=pathlib.PurePosixPath(m.name).name.lower()
    if m.isfile() and m.size<2_000_000 and re.match(r'^(copying|copyright|licen[cs]e|notice|authors)([._-]|$)',base):
     content=tf.extractfile(m).read();out=S/'notices'/p.name/pathlib.PurePosixPath(m.name)
     if '..' in out.parts or pathlib.PurePosixPath(m.name).is_absolute():continue
     out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(content);notices.append({'source':p.name,'member':m.name,'file':str(out.relative_to(S)),'sha256':hashlib.sha256(content).hexdigest()})
 except Exception as e:print('NOTICE ERROR',p,e,flush=True)
(S/'notice-index.json').write_text(json.dumps(notices,indent=2))
print(json.dumps({'files':len(results),'verified':sum(x['verified'] for x in results),'notices':len(notices),'extras':extra},indent=2))
