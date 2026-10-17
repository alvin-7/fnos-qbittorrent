"""Exercise final 1.2.2 packaged bytes with isolated native1.1.9 real regressions."""
from pathlib import Path
import subprocess, os
R=Path(__file__).resolve().parents[1]
D=R/'.runtime/regression123';D.mkdir(exist_ok=True)
for name in ['verify_pt119_real.py','verify_pt119_browser.mjs','verify_diagnostics119_real.py','verify_diagnostics119_browser.mjs']:
    s=(R/'tools'/name).read_text().replace('.runtime/package119','.runtime/package123')
    # Keep original fixture ports and mechanics; never replace immutable prior evidence.
    s=s.replace('.runtime/pt119','.runtime/pt123').replace('.runtime/diagnostics119','.runtime/diagnostics123')
    s=s.replace('evidence/pt119','evidence/pt123').replace('evidence/diagnostics119','evidence/diagnostics123')
    if name.endswith('.py'):
        s=s.replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')')
        s=s.replace('tools/verify_pt119_browser.mjs','.runtime/regression123/verify_pt119_browser.mjs').replace('tools/verify_diagnostics119_browser.mjs','.runtime/regression123/verify_diagnostics119_browser.mjs')
    s=s.replace('const u=http.request({socketPath:', "for(const k of Object.keys(req.headers))if(k.toLowerCase().startsWith('x-trim-'))delete req.headers[k];delete req.headers.cookie;const u=http.request({socketPath:") if name.endswith('.mjs') else s
    (D/name).write_text(s)
for name in ['verify_pt119_real.py','verify_diagnostics119_real.py']:
    subprocess.run(['python3',str(D/name)],cwd=R,check=True)
