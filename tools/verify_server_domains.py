import json, pathlib, subprocess, os, tempfile, sys
r=pathlib.Path(__file__).resolve().parents[1]; cmd=r/'fnos-qbittorrent/cmd'; tmp=pathlib.Path(tempfile.mkdtemp()); cfg=tmp/'qBittorrent.conf'
env=dict(os.environ,QBT_IPV4_ADDRESSES='inet 192.168.1.20/24\ninet 10.2.3.4/16',wizard_host='',TRIM_PKGVAR=str(tmp/'var'),TRIM_DATA_SHARE_PATHS=str(tmp/'downloads'))
(tmp/'downloads').mkdir(); subprocess.run([sys.executable,str(cmd/'refresh_server_domains.py'),str(cfg)],env=env,check=True)
text=cfg.read_text(); assert 'localhost;127.0.0.1;10.2.3.4;192.168.1.20' in text
cfg.write_text('[Preferences]\nWebUI\\ServerDomains="custom.example;192.168.1.20"\nWebUI\\Password_PBKDF2=keep\n')
env['QBT_IPV4_ADDRESSES']='inet 192.168.1.21/24'; env['wizard_host']='nas.example'; subprocess.run([sys.executable,str(cmd/'refresh_server_domains.py'),str(cfg)],env=env,check=True)
text=cfg.read_text(); assert 'custom.example' in text and 'nas.example' in text and '192.168.1.21' in text and '192.168.1.20' not in text and 'Password_PBKDF2=keep' in text
print(json.dumps({'domain_refresh':0,'custom_and_password_preserved':0,'dhcp_refresh':0}))
