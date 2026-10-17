import os,pathlib,subprocess,json,shutil,urllib.request,urllib.parse,http.cookiejar,time,re
r=pathlib.Path(__file__).resolve().parents[1];d=r/'.runtime/package-run';d.mkdir(parents=True,exist_ok=True);(d/'downloads').mkdir(exist_ok=True)
env=dict(os.environ,TRIM_APPDEST=str(r/'fnos-qbittorrent/app'),TRIM_PKGVAR=str(d/'var'),TRIM_DATA_SHARE_PATHS=str(d/'downloads'),TRIM_UID=str(os.getuid()),TRIM_GID=str(os.getgid()),TRIM_SERVICE_PORT='18081',wizard_host='127.0.0.1')
# Test exact package preparation, but keep container and external port equal for upstream Host validation.
subprocess.run([str(r/'fnos-qbittorrent/cmd/install_callback')],env=env,check=True)
c=d/'var/config/qBittorrent/config/qBittorrent.conf';c.write_text(c.read_text().replace('Port=18080','Port=18081'))
name='fnos-qbt-package-validation';subprocess.run(['docker','rm','-f',name],capture_output=True)
args=['docker','run','-d','--name',name,'--user',f'{os.getuid()}:{os.getgid()}','--cap-drop=ALL','--security-opt=no-new-privileges:true','-p','127.0.0.1:18081:18081','-e','QBT_LEGAL_NOTICE=confirm','-v',str(d/'var/config')+':/config','-v',str(d/'downloads')+':/downloads','-v',str(r/'fnos-qbittorrent/app/webui')+':/webui:ro','ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1']
try:
 subprocess.run(args,check=True,capture_output=True)
 for _ in range(30):
  time.sleep(1);logs=subprocess.check_output(['docker','logs',name],stderr=subprocess.STDOUT).decode();m=re.search(r'temporary password is provided for this session: (\S+)',logs)
  if m:break
 else:raise RuntimeError('non-root container did not start')
 op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()));base='http://127.0.0.1:18081';page=op.open(base).read();assert '轻下载'.encode() in page
 response=op.open(base+'/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':m[1]}).encode());assert response.status==204
 version=op.open(base+'/api/v2/app/version').read().decode();assert version=='v5.2.4';result={'nonroot_uid':os.getuid(),'cap_drop':'ALL','no_new_privileges':True,'version':version,'served_packaged_custom_ui':True,'host_validation_kept':True};(r/'evidence/packaged-runtime.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:subprocess.run(['docker','rm','-f',name],capture_output=True)
