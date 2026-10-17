"""Isolated real pinned qB; old packaged false-error reproduction or final cycle."""
from pathlib import Path
import os,subprocess
R=Path(__file__).resolve().parents[1]
source=(R/'tools/verify_pt119_real.py').read_text().split('\ntry:\n')[0].replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')').replace('.runtime/pt119','.runtime/ratio128')
exec(source)
q=QB('ratio',18137,16937)
try:
 old=os.environ.get('RATIO_OLD')=='1';pkg='package127' if old else 'package128'
 q.prefs(save_path=str(q.download),temp_path=str(q.download/'incomplete'),alternative_webui_enabled=True,alternative_webui_path=str(R/('.runtime/'+pkg+'/app/webui')))
 subprocess.run(['node','tools/verify_ratio128.mjs'],cwd=R,env=dict(os.environ,RATIO_COOKIE=q.cookie),check=True)
finally:q.stop()
