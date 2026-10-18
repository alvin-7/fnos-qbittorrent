"""Immutable 1.5.12 application rebuild over locked historical runtime, NOT clean rebuild."""
from pathlib import Path
R = Path(__file__).resolve().parents[1]
s = (R / 'tools/build_native_1_5_11.py').read_text()
s = s.replace('1.5.11', '1.5.12').replace('directory161-build', 'release1512-build').replace('package161', 'package1512').replace('workspace161-artifact', 'release1512-artifact')
a = s.index("for n in ['src'")
b = s.index('materials=', a)
s = s[:a] + '''# Explicit public inventory excludes local fixtures, evidence and archives.
paths=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=R).decode().split('\\0')
for name in sorted(set(filter(None,paths))):
 p=R/name
 assert p.is_file() and not p.is_symlink(),name
 assert not any(part in {'.runtime','release','evidence','node_modules','dist','native-package'} for part in p.relative_to(R).parts),name
 dst=app/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
# Include effective lightweight packaging metadata, never inherited binaries.
for name in ['manifest','config/resource']:
 dst=app/'native-package'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stage/name,dst)
for name in ['cmd','wizard','ui']:
 if (stage/name).is_dir():shutil.copytree(stage/name,app/'native-package'/name)
''' + s[b:]
s = s.replace("'retained_source_sha256':sha(REL/'native-1.4.8-source-bundle.tar.gz')", "'retained_source_sha256':sha(REL/'native-1.5.1-source-bundle.tar.gz')")
s = s.replace("D.mkdir();stage.mkdir();", "D.mkdir();stage.mkdir();(R/'evidence').mkdir(exist_ok=True);")
exec(compile(s, str(R/'tools/build_native_1_5_11.py'), 'exec'))
