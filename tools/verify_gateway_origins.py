"""Migration and fail-closed origin configuration regressions."""
from pathlib import Path
import tempfile,subprocess,os
root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(dir=root/'.runtime') as tmp:
 p=Path(tmp)/'gateway-origins'; old=Path(tmp)/'config/qBittorrent/config/qBittorrent.conf.auto-server-domains';old.parent.mkdir(parents=True)
 old.write_text('localhost;127.0.0.1;192.168.1.5;old.example')
 script=root/'fnos-qbittorrent/cmd/refresh_gateway_origins.py'
 def run(**env):return subprocess.run(['python3',str(script),str(p)],env=dict(os.environ,wizard_host='',wizard_gateway_origins='',**env),capture_output=True)
 assert run().returncode==0
 assert p.read_text()=='https://old.example\n'
 assert p.stat().st_mode&0o777==0o600
 old.write_text('localhost;127.0.0.1')
 assert run().returncode==0 and p.read_text()=='https://old.example\n'
 for value in ['https://*.example','https://user:secret@example','https://example/path','https://example?secret=x','https://example:bad']:
  result=subprocess.run(['python3',str(script),str(p)],env=dict(os.environ,wizard_host='',wizard_gateway_origins=value),capture_output=True)
  assert result.returncode!=0,value
  assert p.read_text()=='https://old.example\n'
 print('Origins migration, persistence, mode and invalid configuration rejection passed')
