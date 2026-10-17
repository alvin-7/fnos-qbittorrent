import hashlib,pathlib
r=pathlib.Path(__file__).resolve().parents[1]; p=r/'tests/fixtures';p.mkdir(parents=True,exist_ok=True)
def b(x):
 if isinstance(x,int):return b'i'+str(x).encode()+b'e'
 if isinstance(x,bytes):return str(len(x)).encode()+b':'+x
 if isinstance(x,dict):return b'd'+b''.join(b(k)+b(v) for k,v in sorted(x.items()))+b'e'
data=b'This is a local, lawful integration fixture. No tracker, no public swarm.\n'
info={b'name':b'legal-test.txt',b'length':len(data),b'piece length':16384,b'pieces':hashlib.sha1(data).digest(),b'private':1}
(p/'legal-test.torrent').write_bytes(b({b'info':info}));(r/'.runtime/downloads/legal-test.txt').write_bytes(data)
(r/'evidence/fixture.json').write_text(__import__('json').dumps({'hash':hashlib.sha1(b(info)).hexdigest(),'length':len(data),'private':True,'tracker':None},indent=2))
