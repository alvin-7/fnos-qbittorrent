import pathlib,shutil,json,subprocess,hashlib,zlib,struct
r=pathlib.Path(__file__).resolve().parents[1];app=r/'fnos-qbittorrent/app';licenses=app/'licenses';licenses.mkdir(exist_ok=True)
version=(r/'fnos-qbittorrent/manifest').read_text().split('version=',1)[1].splitlines()[0].strip()
for src,dst in [('evidence/qbittorrent-COPYING','qBittorrent-COPYING'),('evidence/docker-LICENSE','GPL-3.0.txt'),('evidence/upstream-sbom.txt','upstream-sbom.txt'),('evidence/image-source.json','image-source.json'),('THIRD_PARTY_NOTICES.md','THIRD_PARTY_NOTICES.md'),('evidence/upstream-docker-README.md','official-image-readme.md')]:shutil.copyfile(r/src,licenses/dst)
deps=[]
for name in ['react','react-dom','scheduler']:
 p=r/'node_modules'/name; d=json.loads((p/'package.json').read_text());deps.append({k:d.get(k) for k in ['name','version','license','repository']});shutil.copyfile(p/'LICENSE',licenses/(name+'-LICENSE'))
(licenses/'frontend-dependencies.json').write_text(json.dumps(deps,indent=2))
if (app/'webui').exists(): shutil.rmtree(app/'webui')
shutil.copytree(r/'webui',app/'webui')
# Own minimal blue download icon, generated from original geometry, not upstream trademark.
def icon(n):
 data=bytearray()
 for y in range(n):
  data.append(0)
  for x in range(n):
   arrow=(abs(x-n*.5)<n*.055 and n*.22<y<n*.57) or (n*.45<y<n*.68 and abs(x-n*.5)<(n*.68-y)) or (n*.74<y<n*.8 and n*.25<x<n*.75)
   data.extend((255,255,255,255) if arrow else (57,117,238,255))
 def chunk(t,d):return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d))
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',n,n,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(data))+chunk(b'IEND',b'')
for n in [64,256]:
 raw=icon(n);(app/'ui/images'/f'icon_{n}.png').write_bytes(raw);(r/'fnos-qbittorrent'/('ICON.PNG' if n==64 else 'ICON_256.PNG')).write_bytes(raw)
subprocess.run([str(r/'tools/fnpack'),'build','--directory',str(r/'fnos-qbittorrent')],cwd=r,check=True)
release=r/'release';release.mkdir(exist_ok=True);p=release/f'fnos-qbittorrent-{version}-x86_64.fpk';shutil.copyfile(r/'fnos-qbittorrent.fpk',p)
(release/'SHA256SUMS').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
print(str(p),p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
