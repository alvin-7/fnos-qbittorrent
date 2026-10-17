"""Real qB 5.2.4 + compiled proxy regression; only isolated test state is changed."""
import os, pathlib, subprocess, time, json, re, http.client, socket, urllib.parse
r=pathlib.Path(__file__).resolve().parents[1]
d=r/'.runtime/gateway-regression'; d.mkdir(parents=True,exist_ok=True)
image='ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1'
net='fnos-qbt-gateway-regression'; qb='fnos-qbt-gateway-core-test'; gw='fnos-qbt-gateway-proxy-test'
report={}
def run(*args): return subprocess.check_output(args,stderr=subprocess.STDOUT).decode().strip()
def request(path='/api/v2/app/version',body=None,headers=None,via='gateway'):
    h={'Host':'nas.test:5666'} if via=='gateway' else {'Host':'127.0.0.1:18080'}
    h.update(headers or {})
    if body is not None: h['Content-Type']='application/x-www-form-urlencoded'
    if via=='gateway':
        c=http.client.HTTPConnection('localhost',timeout=5);c.sock=socket.socket(socket.AF_UNIX);c.sock.connect(str(d/'app.sock'));path='/app/fnos-qbittorrent'+path
    else: c=http.client.HTTPConnection('127.0.0.1',18082,timeout=5)
    c.request('POST' if body is not None else 'GET',path,body,h);res=c.getresponse()
    res_headers={k:v for k,v in res.getheaders() if k.lower() not in ('set-cookie','cookie','authorization')}
    # Session cookies are used only in memory for this isolated test.
    session=next((v.split(';')[0] for k,v in res.getheaders() if k.lower()=='set-cookie'),'')
    result={'status':res.status,'body':res.read().decode(),'headers':res_headers};c.close()
    if session: request.session=session
    return result
for name in (gw,qb): subprocess.run(['docker','rm','-f',name],capture_output=True)
subprocess.run(['docker','network','rm',net],capture_output=True)
run('docker','network','create','--internal','--subnet','172.30.247.0/29',net)
config=d/'config/qBittorrent/config';config.mkdir(parents=True,exist_ok=True)
(d/'downloads').mkdir(exist_ok=True)
# Use production prepare, including upgrade migration, not a hand-written trust config.
env=dict(os.environ,TRIM_PKGVAR=str(d),TRIM_DATA_SHARE_PATHS=str(d/'downloads'),wizard_host='nas.test',wizard_gateway_origins='https://nas.test https://nas.test:5666 http://127.0.0.1:18083')
subprocess.run([str(r/'fnos-qbittorrent/cmd/prepare')],env=env,check=True)
import shutil
shutil.copyfile(r/'fnos-qbittorrent/app/docker/gateway',d/'gateway')
(d/'gateway').chmod(0o755)
try:
    run('docker','run','-d','--name',qb,'--network',net,'--ip','172.30.247.2','--network-alias','qbittorrent','-p','127.0.0.1:18082:18080','-e','QBT_LEGAL_NOTICE=confirm','-e','QBT_WEBUI_PORT=18080','-v',str(d/'config')+':/config','-v',str(d/'downloads')+':/downloads','-v',str(r/'fnos-qbittorrent/app/webui')+':/webui:ro',image)
    # A separate non-trusted network also gives qB a normal egress/default route.
    run('docker','network','connect','bridge',qb)
    run('docker','run','-d','--name',gw,'--network',net,'--ip','172.30.247.3','--user',f'{os.getuid()}:{os.getgid()}','--cap-drop=ALL','--security-opt=no-new-privileges:true','-e','GATEWAY_SOCKET=/test/app.sock','-e','BACKEND_URL=http://qbittorrent:18080','-e','GATEWAY_ORIGINS_FILE=/test/gateway-origins','-v',str(d)+':/test','--entrypoint','/test/gateway',image)
    for _ in range(40):
        try:
            if (d/'app.sock').exists() and request()['status']!=502: break
        except (OSError,http.client.HTTPException): pass
        time.sleep(.5)
    untrusted=subprocess.run(['docker','run','--rm','--network',net,'--ip','172.30.247.4','--entrypoint','wget',image,'-S','-O','-','--header=Host: 127.0.0.1:18080','http://qbittorrent:18080/api/v2/app/version'],capture_output=True,text=True)
    report['other_internal_peer']={'source':'172.30.247.4','response':untrusted.stdout+untrusted.stderr}
    assert '403 Forbidden' in report['other_internal_peer']['response'],report
    report['gateway_source']=json.loads(run('docker','inspect',gw))[0]['NetworkSettings']['Networks'][net]['IPAddress']
    report['gateway_no_qb_session']=request()
    assert report['gateway_no_qb_session']['status']==200 and report['gateway_no_qb_session']['body']=='v5.2.4',report
    report['browser_referer']=request(headers={'Referer':'https://nas.test:5666/app/fnos-qbittorrent/'})
    assert report['browser_referer']['status']==200,report
    prefs=request('/api/v2/app/preferences',headers={'Referer':'https://nas.test:5666/app/fnos-qbittorrent/'})
    assert prefs['status']==200,prefs
    p=json.loads(prefs['body']);old=p['dl_limit'];assert p['web_ui_csrf_protection_enabled'] and p['web_ui_host_header_validation_enabled']
    body=urllib.parse.urlencode({'json':json.dumps({'dl_limit':125952})})
    report['settings_write']=request('/api/v2/app/setPreferences',body,{'Origin':'https://nas.test:5666'})
    assert report['settings_write']['status']==200,report
    assert json.loads(request('/api/v2/app/preferences')['body'])['dl_limit']==125952
    request('/api/v2/app/setPreferences',urllib.parse.urlencode({'json':json.dumps({'dl_limit':old})}),{'Origin':'https://nas.test:5666'})
    report['cross_origin']=request('/api/v2/app/setPreferences',body,{'Origin':'https://evil.test'})
    assert report['cross_origin']['status']==403,report
    report['direct_spoofed_trim']=request(via='direct',headers={'X-Trim-Userid':'admin','X-Trim-Isadmin':'true','X-Forwarded-For':'172.30.247.3'})
    assert report['direct_spoofed_trim']['status']==403,report # qB auth failure is 403 in 5.2.4
    report['direct_public_ui']=request('/',via='direct')['status'];assert report['direct_public_ui']==200
    logs=run('docker','logs',qb);password=re.findall(r'temporary password is provided for this session: (\S+)',logs)[-1]
    login=request('/api/v2/auth/login',urllib.parse.urlencode({'username':'admin','password':password}),via='direct');assert login['status']==204,login
    cookie=request.session
    report['direct_authenticated']=request(via='direct',headers={'Cookie':cookie})
    assert report['direct_authenticated']['body']=='v5.2.4',report
    normal_headers={'Cookie':cookie,'Origin':'http://127.0.0.1:18080'}
    report['direct_settings_write']=request('/api/v2/app/setPreferences',body,normal_headers,via='direct')
    assert report['direct_settings_write']['status']==200,report
    assert json.loads(request('/api/v2/app/preferences',headers={'Cookie':cookie},via='direct')['body'])['dl_limit']==125952
    request('/api/v2/app/setPreferences',urllib.parse.urlencode({'json':json.dumps({'dl_limit':old})}),normal_headers,via='direct')
    report['direct_settings_read_write_verified']=True
    report['direct_bad_host']=request(via='direct',headers={'Cookie':cookie,'Host':'evil.test:18080'})
    report['direct_bad_origin']=request('/api/v2/app/setPreferences',body,{'Cookie':cookie,'Origin':'https://evil.test'},via='direct')
    assert report['direct_bad_host']['status']==401 and report['direct_bad_origin']['status']==401,report
    browser=subprocess.run(['node',str(r/'tools/verify_gateway_browser.mjs'),str(d/'app.sock')],cwd=r,env=dict(os.environ,QBT_TEST_PASSWORD=password),capture_output=True,text=True)
    report['browser_prefix']=browser.stdout+browser.stderr
    assert browser.returncode==0,report['browser_prefix']
    report['rewritten_host']=request(headers={'Host':'fnconnect.internal','Origin':'https://nas.test:5666'})
    assert report['rewritten_host']['status']==200
    report['navigation_external_referer']=request('/',headers={'Host':'fnconnect.internal','Referer':'https://external.example/','Sec-Fetch-Site':'cross-site'})['status']
    assert report['navigation_external_referer']==200
    report['missing_source_mutation']=request('/api/v2/app/setPreferences','json=%7B%7D')['status']
    assert report['missing_source_mutation']==403
    report['trust_config']=[s for s in (config/'qBittorrent.conf').read_text().splitlines() if 'AuthSubnet' in s or 'ReverseProxy' in s]
    report['settings_read_write_verified']=True
finally:
    (r/'evidence/gateway-regression.json').write_text(json.dumps(report,indent=2))
    for name in (gw,qb): subprocess.run(['docker','rm','-f',name],capture_output=True)
    import shutil
    if (d/'config').exists(): shutil.rmtree(d/'config')
    subprocess.run(['docker','network','rm',net],capture_output=True)
print(json.dumps(report,indent=2))
