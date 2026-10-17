import pathlib,subprocess,os,tempfile,json,hashlib
r=pathlib.Path(__file__).resolve().parents[1]; result={};scratch=r/'.runtime/lifecycle';scratch.mkdir(parents=True,exist_ok=True)
env=dict(os.environ,TRIM_PKGVAR=str(scratch/'var'),TRIM_DATA_SHARE_PATHS=str(scratch/'downloads'),TRIM_TEMP_LOGFILE=str(scratch/'error'),wizard_host='')
(scratch/'downloads').mkdir(exist_ok=True)
cmd=r/'fnos-qbittorrent/cmd'
for f in cmd.iterdir():
 if f.is_file() and f.suffix != '.py':
  x=subprocess.run(['bash','-n',str(f)]);assert x.returncode==0
result['bash_syntax']=0
assert subprocess.run([str(cmd/'install_callback')],env=env).returncode==0
file=scratch/'var/config/qBittorrent/config/qBittorrent.conf';before=file.read_bytes();assert b'"localhost;127.0.0.1;' in before
assert b'HostHeaderValidation=true' in before and b'CSRFProtection=true' in before
assert file.stat().st_mode&0o777==0o600
for f in ['upgrade_callback','config_callback','uninstall_init','uninstall_callback']:
 assert subprocess.run([str(cmd/f)],env=env).returncode==0
 assert file.read_bytes()==before
result['prepare_upgrade_uninstall_preserves_config']=0
for op,expected in [('start',0),('stop',0),('status',3),('invalid',1)]:
 code=subprocess.run([str(cmd/'main'),op],env=env).returncode;assert code==expected;result['main_'+op]=code
for f in ['config/privilege','config/resource','app/ui/config','wizard/install','wizard/config','wizard/upgrade','wizard/uninstall']:json.loads((r/'fnos-qbittorrent'/f).read_text())
result['json_validation']=0
(r/'evidence/lifecycle.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
