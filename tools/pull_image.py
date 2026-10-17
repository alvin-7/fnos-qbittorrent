import urllib.request,json,tarfile,hashlib,pathlib
root=pathlib.Path(__file__).resolve().parents[1]; out=root/'evidence/image'; out.mkdir(parents=True,exist_ok=True)
repo='qbittorrent/docker-qbittorrent-nox'; tag='5.2.4-1'; reg='https://ghcr.io'
def get(url,headers={}):
 return urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=180).read()
token=json.loads(get(f'{reg}/token?service=ghcr.io&scope=repository:{repo}:pull'))['token']; headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json'}
raw=get(f'{reg}/v2/{repo}/manifests/{tag}',headers); digest='sha256:'+hashlib.sha256(raw).hexdigest(); m=json.loads(raw)
if 'manifests' in m:
 d=next(x['digest'] for x in m['manifests'] if x.get('platform',{}).get('architecture')=='amd64' and x['platform']['os']=='linux'); raw=get(f'{reg}/v2/{repo}/manifests/{d}',headers); m=json.loads(raw)
files=[]
for b in [m['config']]+m['layers']:
 d=b['digest']; name=d.split(':')[1]+('.json' if b==m['config'] else '.tar.gz'); p=out/name
 if not p.exists(): p.write_bytes(get(f'{reg}/v2/{repo}/blobs/{d}',headers))
 assert hashlib.sha256(p.read_bytes()).hexdigest()==d.split(':')[1]; files.append(name); print(name,p.stat().st_size,flush=True)
ref=f'ghcr.io/{repo}:{tag}'; (out/'manifest.json').write_text(json.dumps([{'Config':files[0],'RepoTags':[ref],'Layers':files[1:]}]))
with tarfile.open(out/'image.tar','w') as t:
 for f in files+['manifest.json']: t.add(out/f,arcname=f)
(root/'evidence/image-source.json').write_text(json.dumps({'image':ref,'index_digest':digest,'manifest':m},indent=2)); print(ref,digest)
