#!/usr/bin/env python3
"""Read-only, redacted fnOS contract probe. Run as the installed package account.
Never prints environment values, paths, tokens, messages, or response bodies.
"""
import http.client,json,os,socket
APP='fnos-qbittorrent-native'
class Unix(http.client.HTTPConnection):
 def connect(self):
  self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(3);self.sock.connect('/var/run/trim_open_gateway_apiscope.socket')
def main():
 report={'probe':'directory-contract-v1','uid':os.getuid()}
 # Require exactly one matching process belonging to this account. Do not guess
 # environment from an interactive SSH shell or read credentials of other users.
 found=[]
 for name in os.listdir('/proc'):
  if not name.isdecimal():continue
  base='/proc/'+name
  try:
   if os.stat(base).st_uid!=os.getuid():continue
   exe=os.readlink(base+'/exe')
   if exe.endswith('/bin/gateway') and APP in exe:found.append(base)
  except OSError:pass
 if len(found)!=1:report['reason']='GATEWAY_PROCESS_NOT_UNIQUE';print(json.dumps(report));return
 try:
  with open(found[0]+'/environ','rb') as f:raw=f.read(1<<20)
  env=dict(x.split(b'=',1) for x in raw.split(b'\0') if b'=' in x)
 except OSError:report['reason']='GATEWAY_ENV_UNREADABLE';print(json.dumps(report));return
 for key in ['TRIM_DATA_SHARE_PATHS','TRIM_DATA_ACCESSIBLE_PATHS']:
  value=env.get(key.encode(),b'');report[key]={'present':bool(value),'colon_entry_count':len(value.split(b':')) if value else 0,'empty_entries':any(not x for x in value.split(b':')) if value else False}
 token=env.get(b'TRIM_API_TOKEN',b'').decode('utf-8',errors='strict');report['token_present']=bool(token)
 if not token:report['reason']='AUTH_TOKEN_MISSING';print(json.dumps(report));return
 c=Unix('localhost',timeout=3)
 try:
  c.request('POST','/api/v1/trimapp',body=json.dumps({'reqId':'safe-contract-probe','req':'trim.file.getSharedAccessibleFolders','appName':APP,'data':{}}),headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  response=c.getresponse();report['http_status']=response.status;raw=response.read((1<<20)+1)
  if len(raw)>1<<20:raise ValueError()
  d=json.loads(raw);report['code']=d.get('code') if type(d.get('code')) is int else 'invalid'
  data=d.get('data');paths=data.get('paths') if isinstance(data,dict) else None
  report['data_type']=type(data).__name__;report['paths_type']=type(paths).__name__
  if isinstance(paths,list):report['path_count']=len(paths);report['all_paths_strings']=all(isinstance(x,str) for x in paths)
 except (OSError,ValueError,http.client.HTTPException):report['reason']='API_TRANSPORT_OR_PARSE_FAILURE'
 finally:c.close()
 print(json.dumps(report,ensure_ascii=True))
if __name__=='__main__':main()
