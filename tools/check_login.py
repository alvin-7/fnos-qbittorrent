import urllib.request,urllib.parse,pathlib
p=pathlib.Path('.runtime/password').read_text().strip()
r=urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:18080/api/v2/auth/login',data=urllib.parse.urlencode({'username':'admin','password':p}).encode()))
print('login response',repr(r.read()),r.status)
