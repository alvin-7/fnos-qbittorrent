"""Register authored design artifacts in Windows OpenDesign; no business APIs."""
from pathlib import Path
import json, urllib.request, hashlib
BASE='http://localhost:10012/api/projects'
ID='fnos-pt-workspace-redesign'
ROOT=Path(__file__).resolve().parent

def request(url, payload=None):
    req=urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=180) as r:return r.read()

project=json.loads(request(BASE,dict(id=ID,name='飞牛 PT · 工作空间重设计 · 桌面与手机',skillId=None,designSystemId=None,conversationMode='design',metadata=dict(kind='prototype',designOnly=True,mockDataOnly=True,authorship='API-authored; not built-in AI generation',reference='Smi13zZ/qbpanel; MIT; no code or brand copied'))))
verified=json.loads(request(BASE+'/'+ID))
(ROOT/'project.json').write_text(json.dumps(verified,ensure_ascii=False,indent=2))
source=(ROOT/'workspace.html').read_text()
files=[]
for name,title in [('desktop.html','桌面工作空间'),('mobile.html','手机工作空间')]:
    content=source.replace('<title>飞牛 PT · 工作空间设计预览</title>',f'<title>飞牛 PT · {title} · 设计预览</title>')
    (ROOT/name).write_text(content)
    result=json.loads(request(BASE+'/'+ID+'/files',dict(name=name,content=content,encoding='utf8',artifact=True,overwrite=False)))
    actual=request(BASE+'/'+ID+'/files/'+name)
    # File route returns raw bytes on this installation.
    if actual!=content.encode():
        parsed=json.loads(actual)
        assert parsed.get('content')==content, list(parsed)
    files.append(dict(name=name,registration=result,sha256=hashlib.sha256(content.encode()).hexdigest()))
(ROOT/'registration.json').write_text(json.dumps(files,ensure_ascii=False,indent=2))
listing=json.loads(request(BASE+'/'+ID+'/files'))
(ROOT/'registered-files.json').write_text(json.dumps(listing,ensure_ascii=False,indent=2))
for name,width,height in [('desktop',1440,1024),('mobile',390,844)]:
    image=request(BASE+'/'+ID+'/export/image',dict(fileName=name+'.html',deck=False,imageFormat='png',width=width,height=height))
    assert image.startswith(b'\x89PNG\r\n\x1a\n'),image[:200]
    (ROOT/(name+'.png')).write_bytes(image)
    print(name,'exported PNG',len(image))
print(json.dumps(verified,ensure_ascii=False))
