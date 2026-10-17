"""Exercise final 1.2.2 packaged bytes with isolated native1.1.9 real regressions."""
from pathlib import Path
import subprocess, os
R=Path(__file__).resolve().parents[1]
D=R/'.runtime/regression122';D.mkdir(exist_ok=True)
for name in ['verify_pt119_real.py','verify_pt119_browser.mjs','verify_diagnostics119_real.py','verify_diagnostics119_browser.mjs']:
    s=(R/'tools'/name).read_text().replace('.runtime/package119','.runtime/package122')
    # Keep original fixture ports and mechanics; never replace immutable prior evidence.
    s=s.replace('evidence/pt119','evidence/pt122').replace('evidence/diagnostics119','evidence/diagnostics122')
    if name.endswith('.py'):
        s=s.replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')')
        s=s.replace('tools/verify_pt119_browser.mjs','.runtime/regression122/verify_pt119_browser.mjs').replace('tools/verify_diagnostics119_browser.mjs','.runtime/regression122/verify_diagnostics119_browser.mjs')
    (D/name).write_text(s)
for name in ['verify_pt119_real.py','verify_diagnostics119_real.py']:
    subprocess.run(['python3',str(D/name)],cwd=R,check=True)
