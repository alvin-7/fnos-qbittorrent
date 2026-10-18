from pathlib import Path
import json, urllib.request
R=Path(__file__).resolve().parent
B='http://localhost:10012/api/projects/fnos-pt-workspace-redesign'
def req(url,payload=None):
    with urllib.request.urlopen(urllib.request.Request(url,data=json.dumps(payload).encode() if payload is not None else None,headers={'Content-Type':'application/json'}),timeout=180) as r:return r.read()
s=(R/'workspace.html').read_text()
listing=req(B+'/files').decode()
for n,title,w,h in [('desktop','桌面工作空间',1440,1024),('mobile','手机工作空间',390,844),('desktop-analysis','桌面分析',1440,1024),('mobile-analysis','手机分析',390,844)]:
    c=s.replace('<title>飞牛 PT · 工作空间设计预览</title>',f'<title>飞牛 PT · {title} · 设计预览</title>')
    if n.endswith('analysis'):
        c=c.replace("if(location.hash==='#analysis')S.nav='analysis';", "S.nav='analysis';")
    (R/(n+'.html')).write_text(c)
    existing=n+'.html' in listing
    req(B+'/files',dict(name=n+'.html',content=c,encoding='utf8',artifact=not existing,overwrite=existing))
    assert req(B+'/files/'+n+'.html')==c.encode()
    png=req(B+'/export/image',dict(fileName=n+'.html',deck=False,imageFormat='png',width=w,height=h))
    assert png[:8]==b'\x89PNG\r\n\x1a\n';(R/(n+'.png')).write_bytes(png)
    print(n+': registered, exact readback, native PNG exported',flush=True)
(R/'registered-files.json').write_bytes(req(B+'/files'))
(R/'project.json').write_bytes(req(B))
