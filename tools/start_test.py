from pathlib import Path
import subprocess,os,re,time,urllib.request
r=Path(__file__).resolve().parents[1]; d=r/'.runtime'; d.mkdir(mode=0o700,exist_ok=True)
# Fresh container isolation: remove prior qB task/config state before each run.
subprocess.run(['docker','rm','-f','fnos-qbt-test'],capture_output=True)
for child in (d/'config').glob('**/*'):
 if child.is_file(): child.unlink()
c=d/'config/qBittorrent/config'; c.mkdir(parents=True,exist_ok=True); (d/'downloads').mkdir(exist_ok=True)
(c/'qBittorrent.conf').write_text('''[BitTorrent]
Session\\DefaultSavePath=/downloads
Session\\TempPath=/downloads/incomplete
Session\\TempPathEnabled=true
Session\\DHTEnabled=false
Session\\PeXEnabled=false
Session\\LSDEnabled=false
[Preferences]
WebUI\\Port=18080
WebUI\\AlternativeUIEnabled=true
WebUI\\RootFolder=/webui
WebUI\\HostHeaderValidation=true
WebUI\\ServerDomains="localhost;127.0.0.1"
WebUI\\CSRFProtection=true
WebUI\\LocalHostAuth=true
WebUI\\AuthSubnetWhitelistEnabled=true
WebUI\\AuthSubnetWhitelist=127.0.0.1/32
Connection\\UPnP=false
''')
subprocess.run(['docker','run','-d','--name','fnos-qbt-test','--network','bridge','-p','127.0.0.1:18080:18080','-e','QBT_LEGAL_NOTICE=confirm','-e','QBT_WEBUI_PORT=18080','-v',str(d/'config')+':/config','-v',str(d/'downloads')+':/downloads','-v',str(r/'webui')+':/webui:ro','ghcr.io/qbittorrent/docker-qbittorrent-nox:5.2.4-1'],check=True)
p=d/'password'
if p.exists(): p.unlink()
for _ in range(60):
 try:
  try:
   urllib.request.urlopen('http://127.0.0.1:18080/api/v2/app/version',timeout=1).read()
  except urllib.error.HTTPError:
   pass
  text=subprocess.check_output(['docker','logs','fnos-qbt-test'],stderr=subprocess.STDOUT).decode()
  m=re.findall(r'temporary password is provided for this session: (\S+)',text)
  if not m: raise RuntimeError('test qB not ready')
  if m:
   p=d/'password'; p.write_text(m[-1]); p.chmod(0o600)
  print('isolated container ready and WebUI reachable')
  break
 except Exception:
  time.sleep(1)
# Explicit readiness gate: a listening socket alone is not a ready qB process.
assert (d/'password').exists(), 'temporary test password missing'
print('test lifecycle readiness verified')
