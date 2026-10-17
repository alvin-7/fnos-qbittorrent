"""Retry exact distfiles via official upstream source URLs in confined recipe evaluation."""
import pathlib,json,subprocess,concurrent.futures,urllib.request,hashlib,shutil
R=pathlib.Path(__file__).resolve().parents[1];S=R/'release/native-1.1.2-sources';p=S/'alpine-acquisition.json';d=json.loads(p.read_text());urls={}
image='sha256:dd9d91f629c25ea0b7758d3b618ac93c8b254e7b42a09b7f9f9c9b21828f1ba0'
for o in d['origins']:
 text=(S/'aports'/o['origin']/'APKBUILD').read_text()
 # No host mount, no network, read-only, unprivileged; print source, never build.
 res=subprocess.run(['docker','run','--rm','-i','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--entrypoint=/bin/sh',image],input=text+'\nprintf "\\nSOURCE_LIST\\n%s\\n" "$source"\n',text=True,capture_output=True,timeout=20)
 raw=res.stdout.split('SOURCE_LIST\n')[-1]
 for item in raw.split():
  if '::' in item:name,url=item.split('::',1)
  else:name=item.rsplit('/',1)[-1];url=item
  if url.startswith(('http://','https://','ftp://')):urls[(o['origin'],name)]=url
(S/'resolved-upstream-urls.json').write_text(json.dumps([{'origin':k[0],'file':k[1],'url':v} for k,v in urls.items()],indent=2))
def retry(x):
 if x['verified']:return x
 path=S/x['file'];name=path.name;origin=x['origin'];candidates=[urls.get((origin,name))]+[f'https://distfiles.alpinelinux.org/{v}/{name}' for v in ['v3.23','v3.22','v3.21']]
 x['retry_errors']=[]
 for url in filter(None,candidates):
  if not url.startswith(('https://','http://')):continue
  try:
   if path.exists() and hashlib.sha512(path.read_bytes()).hexdigest()==x['expected_sha512']:
    b=path.read_bytes();x.update(verified=True,url=url,sha512=x['expected_sha512'],sha256=hashlib.sha256(b).hexdigest(),bytes=len(b));return x
   tmp=path.with_name(name+'.part')
   with urllib.request.urlopen(url,timeout=100) as r,open(tmp,'wb') as f:shutil.copyfileobj(r,f)
   b=tmp.read_bytes()
   if hashlib.sha512(b).hexdigest()!=x['expected_sha512']:tmp.unlink();raise ValueError('SHA512 mismatch')
   tmp.rename(path);x.update(verified=True,url=url,sha512=x['expected_sha512'],sha256=hashlib.sha256(b).hexdigest(),bytes=len(b));print('OK',x['file'],flush=True);return x
  except Exception as e:x['retry_errors'].append({'url':url,'error':str(e)})
 print('FAIL',x['file'],flush=True);return x
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:d['files']=list(ex.map(retry,d['files']))
p.write_text(json.dumps(d,indent=2));print('VERIFIED',sum(x['verified'] for x in d['files']),'/',len(d['files']))
