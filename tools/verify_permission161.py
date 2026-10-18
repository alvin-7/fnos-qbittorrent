"""Real POSIX ACL and different-identity checks; no NAS permission claim."""
from pathlib import Path
import ctypes,json,os,subprocess,tempfile
R=Path(__file__).resolve().parents[1]
D=R/'.runtime/permission161';D.mkdir(exist_ok=True)
exe=D/'gateway'
sources=[str(p) for p in (R/'gateway').glob('*.go') if not p.name.endswith('_test.go')]
subprocess.run(['go','build','-o',str(exe),*sources],env=dict(os.environ,GO111MODULE='off',CGO_ENABLED='0'),check=True)
lib=ctypes.CDLL('libacl.so.1',use_errno=True)
lib.acl_from_text.argtypes=[ctypes.c_char_p];lib.acl_from_text.restype=ctypes.c_void_p
lib.acl_set_file.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_void_p];lib.acl_free.argtypes=[ctypes.c_void_p]
results={}
with tempfile.TemporaryDirectory(prefix='permission161-') as temp:
 root=Path(temp);os.chmod(root,0o755)
 child=root/'acl-equivalent';child.mkdir()
 # Owner permissions do not grant read; named package-equivalent uid does.
 # Set owner to a different UID in the private container, then add explicit uid ACL.
 docker=['docker','run','--rm','--network','none','-v',f'{exe}:/probe:ro','-v',f'{root}:/fixture','debian:12-slim']
 subprocess.run(docker+['sh','-c','chown 2000:2000 /fixture/acl-equivalent; chmod 000 /fixture/acl-equivalent'],check=True)
 acl=lib.acl_from_text(b'user::---,user:1000:rwx,group::---,mask::rwx,other::---')
 # File owner is different now; set ACL using container's root via host libacl helper.
 helper=D/'set_acl.py'
 helper.write_text('import ctypes\nl=ctypes.CDLL("libacl.so.1",use_errno=True)\nl.acl_from_text.restype=ctypes.c_void_p\nl.acl_set_file.argtypes=[ctypes.c_char_p,ctypes.c_int,ctypes.c_void_p]\na=l.acl_from_text(b"user::---,user:1000:rwx,group::---,mask::rwx,other::---")\nassert l.acl_set_file(b"/fixture/acl-equivalent",0x8000,a)==0,ctypes.get_errno()\n')
 # python image provides libacl on this host's cached Debian-based runtime.
 subprocess.run(['docker','run','--rm','--network','none','-v',f'{root}:/fixture','-v',f'{helper}:/set_acl.py:ro','python:3.11.13-slim-bookworm','python','/set_acl.py'],check=True)
 lib.acl_free(acl)
 for identity in ['1000:1000','2001:2001']:
  out=subprocess.run(['docker','run','--rm','-i','--network','none','--user',identity,'-v',f'{exe}:/probe:ro','-v',f'{root}:/fixture:ro','debian:12-slim','/probe','--directory-worker'],input=json.dumps({'Root':'/fixture','Relative':'acl-equivalent','List':True}).encode(),stdout=subprocess.PIPE,check=True).stdout
  d=json.loads(out);results[identity]={'error':d['Error'],'writable':d['Writable']}
 assert results['1000:1000']['error']=='',results
 assert results['2001:2001']['error']=='package_read_denied',results
 subprocess.run(docker+['sh','-c','chown 1000:1000 /fixture/acl-equivalent; chmod 700 /fixture/acl-equivalent'],check=True)
(D/'acl-identity-result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
