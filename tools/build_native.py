"""Build-only OCI extraction; resulting application needs no Docker."""
import pathlib,subprocess,json,shutil,hashlib,os,tarfile
R=pathlib.Path(__file__).resolve().parents[1]; A=R/'native-package'; T=A/'app'; runtime=T/'runtime'
def run(*a,**kw):return subprocess.check_output(a,**kw).decode().strip()
image='sha256:dd9d91f629c25ea0b7758d3b618ac93c8b254e7b42a09b7f9f9c9b21828f1ba0'
assert json.loads(run('docker','image','inspect',image))[0]['Architecture']=='amd64'
A.mkdir(exist_ok=True); T.mkdir(exist_ok=True);runtime.mkdir(exist_ok=True)
c=run('docker','create',image)
try:
 closure=run('docker','run','--rm','--entrypoint','/bin/sh',image,'-c','ldd /usr/bin/qbittorrent-nox').splitlines()
 paths={'/usr/bin/qbittorrent-nox','/lib/ld-musl-x86_64.so.1','/etc/ssl/cert.pem','/lib/apk/db/installed','/usr/lib/qt6/plugins/tls/libqopensslbackend.so','/usr/lib/qt6/plugins/tls/libqcertonlybackend.so'}
 for line in closure:
  if '=>' in line:paths.add(line.split('=>')[1].strip().split()[0])
 for src in sorted(paths):
  dst=runtime/src.lstrip('/');dst.parent.mkdir(parents=True,exist_ok=True);subprocess.run(['docker','cp','-L',c+':'+src,str(dst)],check=True,stdout=subprocess.DEVNULL)
finally:subprocess.run(['docker','rm',c],check=True,stdout=subprocess.DEVNULL)
# Explicit loader with full closure; all libraries remain private.
libpath=':'.join(str(p) for p in [runtime/'lib',runtime/'usr/lib',runtime/'usr/lib/libproxy'])
v=run(str(runtime/'lib/ld-musl-x86_64.so.1'),'--library-path',libpath,str(runtime/'usr/bin/qbittorrent-nox'),'--version',env=dict(os.environ,QT_PLUGIN_PATH=str(runtime/'usr/lib/qt6/plugins')));assert v=='qBittorrent v5.2.4',v
for d in ['cmd','config','wizard']: (A/d).mkdir(exist_ok=True)
subprocess.run(['npm','run','build'],cwd=R,env=dict(os.environ,VITE_NATIVE='1'),check=True)
if (T/'webui').exists():shutil.rmtree(T/'webui')
for scope in ['public','private']:shutil.copytree(R/'dist',T/'webui'/scope)
for p in (T/'webui').rglob('*.js'):p.write_text(p.read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native'))
shutil.copytree(R/'fnos-qbittorrent/app/ui',T/'ui',dirs_exist_ok=True)
p=T/'ui/config';p.write_text(p.read_text().replace('fnos-qbittorrent.Application','fnos-qbittorrent-native.main').replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native').replace('轻下载 · qBittorrent','轻下载 · qB Native 测试'))
for n in ['ICON.PNG','ICON_256.PNG']:shutil.copyfile(R/'fnos-qbittorrent'/n,A/n)
(A/'manifest').write_text('appname=fnos-qbittorrent-native\nversion=1.1.1\ndisplay_name=轻下载 · qB Native 测试\ndesc=原生 x86_64 qBittorrent-nox 5.2.4 + Unix gateway，独立应用非旧版覆盖升级；NAS待验收。\nplatform=x86\nsource=thirdparty\nmaintainer=Local App Maintainers\ndistributor=Local App Maintainers\ndesktop_uidir=ui\ndesktop_applaunchname=fnos-qbittorrent-native.main\nctl_stop=true\nchangelog=独立原生测试应用，不修改旧Docker应用数据。\n')
(A/'config/privilege').write_text(json.dumps({'defaults':{'run-as':'package'},'username':'qb-native','groupname':'qb-native'}))
(A/'config/resource').write_text(json.dumps({'data-share':{'shares':[{'name':'fnos-qbittorrent-native/downloads'}]}}))
for name in ['install','upgrade','config','uninstall']:(A/'wizard'/name).write_text(json.dumps([{'stepTitle':'原生测试版与迁移','items':[{'type':'tips','helpText':'独立应用，不覆盖旧版。先停止旧版避免端口冲突；不自动导入 /downloads 或删除数据。迁移请按指南备份、指定真实路径、暂停添加后重新校验。统一网关管理员入口，NAS待验收。'}]}],ensure_ascii=False))
for name in ['install_init','upgrade_init','uninstall_init','uninstall_callback','config_init']:
 p=A/'cmd'/name;p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
for name in ['install_callback','upgrade_callback','config_callback']:
 p=A/'cmd'/name;p.write_text('#!/bin/sh\nset -eu\nexec "$TRIM_APPDEST/bin/native-control" prepare\n');p.chmod(0o755)
p=A/'cmd/main';p.write_text('#!/bin/sh\nset -eu\nexec "$TRIM_APPDEST/bin/native-control" "$@"\n');p.chmod(0o755)
(T/'bin').mkdir(exist_ok=True)
env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0',GOOS='linux',GOARCH='amd64')
subprocess.run(['go','build','-trimpath','-o',str(T/'bin/native-control'),str(R/'native/control.go')],env=env,check=True)
g=R/'.runtime/native-gateway-src';g.mkdir(parents=True,exist_ok=True)
for name in ['proxy.go','session.go','native.go']:
 s=(R/'gateway'/name).read_text().replace('/app/fnos-qbittorrent','/app/fnos-qbittorrent-native')
 if name=='proxy.go':
  s=s.replace('"http://qbittorrent:18080"','"http://127.0.0.1:18080"')
 (g/name).write_text(s)
subprocess.run(['go','build','-trimpath','-o',str(T/'bin/gateway'),*[str(g/n) for n in ['proxy.go','session.go','native.go']]],env=env,check=True)
licenses=T/'licenses';licenses.mkdir(exist_ok=True)
for name in ['qbittorrent-COPYING','docker-LICENSE','upstream-sbom.txt','image-source.json']:
 shutil.copyfile(R/'evidence'/name,licenses/name)
for p in (R/'fnos-qbittorrent/app/licenses').glob('*'):
 if p.is_file():shutil.copyfile(p,licenses/p.name)
(licenses/'NATIVE-SOURCES.md').write_text('Runtime extracted from official qbittorrent/docker-qbittorrent-nox OCI image, config SHA256 dd9d91f629c25ea0b7758d3b618ac93c8b254e7b42a09b7f9f9c9b21828f1ba0. See image-source.json layer digests. qB source: https://github.com/qbittorrent/qBittorrent/tree/release-5.2.4 ; Qt https://download.qt.io/archive/qt/ ; Alpine dependency versions/licenses/source origins: runtime/lib/apk/db/installed and https://gitlab.alpinelinux.org/alpine/aports ; exact source retention remains a distribution gate. musl LGPL Qt libraries dynamically linked using private loader. Build script and native control source delivered alongside FPK. No NAS Docker or apt required.\n')
subprocess.run(['python3',str(R/'tools/collect_native_compliance.py')],cwd=R,check=True)
files={str(p.relative_to(T)):hashlib.sha256(p.read_bytes()).hexdigest() for p in runtime.rglob('*') if p.is_file()}
(licenses/'runtime-sha256.json').write_text(json.dumps(files,indent=2))
(R/'evidence/native-build.json').write_text(json.dumps({'image_config':image,'cli':v,'arch':'x86_64','glibc':'none: private musl loader','dependencies':closure,'files':files},indent=2))
old=R/'fnos-qbittorrent-native.fpk'
if old.exists():old.unlink()
sock=T/'app.sock'
if sock.exists():sock.unlink()
subprocess.run([str(R/'tools/fnpack'),'build','--directory',str(A)],cwd=R,check=True)
assert old.is_file(), 'fnpack did not produce artifact'
p=R/'release/fnos-qbittorrent-native-1.1.1-x86_64.fpk';shutil.copyfile(R/'fnos-qbittorrent-native.fpk',p)
(p.with_suffix('.fpk.sha256')).write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
print(p,hashlib.sha256(p.read_bytes()).hexdigest())
