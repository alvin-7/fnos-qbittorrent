"""Verify effective outer and inner resource, including every duplicate member."""
import io,json,tarfile,sys
from pathlib import Path
SCOPES=['trim.file.sharedAccess','trim.file.userAcl','trim.file.path']
SHARES={'shares':[{'name':'fnos-qbittorrent-native/downloads'}]}
def audit(path):
 result={}
 with tarfile.open(path) as outer:
  with tarfile.open(fileobj=io.BytesIO(outer.extractfile('app.tgz').read())) as inner:
   for label,archive in [('outer',outer),('inner',inner)]:
    members=[m for m in archive.getmembers() if m.name.lstrip('./')=='config/resource']
    assert members,(label,'resource missing')
    for m in members:
     data=json.loads(archive.extractfile(m).read())
     assert data['api-scope']==SCOPES,(label,'scope mismatch',data.get('api-scope'))
     assert data['data-share']==SHARES,(label,'upgrade share identity changed')
    result[label]={'members':len(members),'api-scope':data['api-scope'],'data-share':data['data-share']}
 return result
if __name__=='__main__':print(json.dumps(audit(Path(sys.argv[1])),indent=2))
