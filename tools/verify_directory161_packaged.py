"""Current-source production binary contract; no NAS, qB tasks or credentials.
Run: unshare -Urnm python3 gateway/directories_production_test.py
The private /run contains only a simulated official API socket.
"""
import contextlib, http.client, http.server, json, os, pathlib, re, secrets
import shutil, socket, socketserver, subprocess, tempfile, threading, time

R = pathlib.Path(__file__).resolve().parents[1]
subprocess.run(['mount', '-t', 'tmpfs', 'tmpfs', '/run'], check=True)
with tempfile.TemporaryDirectory(prefix='directories-production-', dir=os.environ['TMPDIR']) as temp:
    d = pathlib.Path(temp)
    import tarfile,io,hashlib
    fpk=R/'release/fnos-qbittorrent-native-1.5.11-x86_64.fpk'
    with tarfile.open(fpk) as t:
        with tarfile.open(fileobj=io.BytesIO(t.extractfile('app.tgz').read())) as a:
            payload=a.extractfile('bin/gateway').read()
    binary=d/'gateway';binary.write_bytes(payload);binary.chmod(0o755)
    roots = [d/'disk1', d/'disk2']
    for root in roots:
        root.mkdir(); (root/'nested').mkdir()
    subprocess.run(['mount','-t','tmpfs','tmpfs',str(roots[1]/'nested')],check=True)
    (roots[0]/'nested'/'ordinary').mkdir(); (roots[1]/'nested'/'ordinary').mkdir()
    (roots[1]/'escape').symlink_to(d)
    mode = ['ok']
    class Platform(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def do_POST(self):
            req=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            assert req['appName']=='fnos-qbittorrent-native'
            if mode[0]=='source': result={'code':200003}
            elif req['req']=='trim.file.getSharedAccessibleFolders': result={'code':0,'data':{'paths':list(map(str,roots))}}
            else:
                assert req['req']=='trim.file.checkUserACL' and req['data']['uid']==1000
                paths=req['data']['path']
                if mode[0]=='schema' and any(p.endswith('/ordinary') for p in paths): result={'code':0,'data':[]}
                else: result={'code':0,'data':[{'path':p,'readable':not(mode[0]=='denied' and p.endswith('/ordinary')),'writable':True} for p in paths]}
            self.send_response(200); self.end_headers(); self.wfile.write(json.dumps(result).encode())
    platform=socketserver.UnixStreamServer('/var/run/trim_open_gateway_apiscope.socket',Platform)
    threading.Thread(target=platform.serve_forever,daemon=True).start()
    private=d/'private'; private.mkdir(); pw=private/'password'; pw.write_text(secrets.token_hex(32)); pw.chmod(0o600)
    sock=d/'gateway.sock'
    marker=re.search(r'r.Header.Get\(csrfHeader\) != "([^"]+)"',(R/'gateway/gateway_native.go').read_text())[1]
    class Unix(http.client.HTTPConnection):
        def connect(self):
            self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM); self.sock.connect(str(sock))
    def request(route,fields):
        c=Unix('localhost',timeout=10)
        c.request('POST','/app/fnos-qbittorrent-native/gateway/directories/'+route,json.dumps(fields),{'X-Trim-Userid':'1000','X-Trim-Isadmin':'true','X-Fnos-CSRF':marker,'Origin':'http://localhost','Content-Type':'application/json'})
        res=c.getresponse(); data=json.loads(res.read()); code=res.status; c.close(); return code,data
    def start(token):
        p=subprocess.Popen([str(binary)],env=dict(os.environ,TRIM_API_TOKEN=token,BACKEND_PASSWORD_FILE=str(pw),BACKEND_URL='http://127.0.0.1:1',GATEWAY_SOCKET=str(sock)),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(200):
            if sock.exists(): return p
            if p.poll() is not None: raise AssertionError('gateway exited')
            time.sleep(.02)
        raise AssertionError('gateway startup timeout')
    g=None
    try:
        g=start(secrets.token_hex(32))
        code,data=request('roots',{}); assert code==200 and len(data['roots'])==2
        for root in data['roots']:
            code,layer=request('browse',{'rootId':root['rootId'],'relativePath':'nested'})
            assert code==200 and [e['name'] for e in layer['entries']]==['ordinary']
        root=data['roots'][1]
        code,layer=request('browse',{'rootId':root['rootId']}); assert code==200 and all(e['name']!='escape' for e in layer['entries'])
        mode[0]='denied'; code,layer=request('browse',{'rootId':root['rootId'],'relativePath':'nested'})
        assert code==200 and layer['reason']=='DIRECTORY_CHILDREN_FILTERED' and layer['diagnostics']['counts']['ACL_API_DENIED']==1
        mode[0]='schema'; code,layer=request('browse',{'rootId':root['rootId'],'relativePath':'nested'})
        assert code==503 and layer['code']=='AUTH_RESPONSE_INVALID'
        mode[0]='source'; code,layer=request('roots',{}); assert code==503 and layer['code']=='AUTH_SCOPE_DENIED'
        mode[0]='ok'; code,layer=request('validate',{'rootId':root['rootId'],'relativePath':'escape'}); assert code==404
        g.terminate(); g.wait(timeout=10); g=None; sock.unlink(missing_ok=True)
        g=start(''); code,layer=request('roots',{}); assert code==503 and layer['code']=='AUTH_TOKEN_MISSING'
        print(json.dumps({'status':'PASS','exact_fpk_gateway_sha256':hashlib.sha256(payload).hexdigest(),'roots':2,'real_nested_tmpfs':True,'child_acl_denial_and_schema':True,'source_failure_and_missing_token':True,'symlink_escape_blocked':True,'NAS_verified':False}))
    finally:
        if g: g.terminate(); g.wait(timeout=10)
        platform.shutdown(); platform.server_close()
        subprocess.run(['umount',str(roots[1]/'nested')],check=True)
