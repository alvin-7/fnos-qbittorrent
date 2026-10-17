import subprocess,shutil
from pathlib import Path
r=Path(__file__).resolve().parents[1]
subprocess.run(['npm','run','build'],cwd=r,check=True)
for scope in ['public','private']:
 dest=r/'webui'/scope
 if dest.exists(): shutil.rmtree(dest)
 dest.mkdir(parents=True,exist_ok=True)
 shutil.copytree(r/'dist',dest,dirs_exist_ok=True)
print('Built public/private alternate WebUI (no symlinks)')
