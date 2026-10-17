// Browser -> HTTP test transport -> exact production Unix proxy -> real qB.
// Test transport simulates fnOS rewriting Host, not an authentication emulator.
import http from 'node:http';
import fs from 'node:fs';
import {chromium} from 'playwright';
const socket=process.argv[2], report={};
const server=http.createServer((req,res)=>{
 const headers={...req.headers,host:'fnconnect.internal'};
 const upstream=http.request({socketPath:socket,path:req.url,method:req.method,headers},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)});
 upstream.on('error',()=>{res.writeHead(502);res.end()});req.pipe(upstream);
});
await new Promise(resolve=>server.listen(18083,'127.0.0.1',resolve));
let browser;
try {
 browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox']});
 const page=await browser.newPage();const failures=[],resources=[];
 page.on('response',r=>{resources.push({path:new URL(r.url()).pathname,status:r.status()});if(r.status()>=400) failures.push(r.url())});
 page.on('pageerror',e=>failures.push(e.message));
 const base='http://127.0.0.1:18083/app/fnos-qbittorrent';
 for(const suffix of ['', '/']) {
  await page.goto(base+suffix);
  await page.getByRole('button',{name:'添加任务',exact:true}).waitFor();
  if(await page.locator('body').evaluate(el=>el.scrollWidth>innerWidth+1))throw Error('overflow');
 }
 await page.getByRole('button',{name:'设置',exact:true}).click();
 await page.getByLabel('下载限速 (KiB/s)').fill('123');
 await page.getByRole('button',{name:'保存设置',exact:true}).click();
 await page.getByText('设置已保存并核验').waitFor();
 const prefs=await page.evaluate(async()=>{const r=await fetch('/app/fnos-qbittorrent/api/v2/app/preferences');return r.json()});
 if(prefs.dl_limit!==123*1024)throw Error('settings readback');
 const links=await page.locator('[src],link[href],a[href]').evaluateAll(es=>es.map(e=>e.getAttribute('src')||e.getAttribute('href')));
 if(links.some(x=>x?.startsWith('/')&&!x.startsWith('/app/fnos-qbittorrent/')))throw Error('prefix escaping link');
 if(!resources.some(x=>x.path.endsWith('.js'))||!resources.some(x=>x.path.endsWith('.css')))throw Error('missing real assets');
 if(failures.length)throw Error(JSON.stringify(failures));
 const login=await page.evaluate(async password=>{const r=await fetch('/app/fnos-qbittorrent/api/v2/auth/login',{method:'POST',body:new URLSearchParams({username:'admin',password})});return r.status},process.env.QBT_TEST_PASSWORD);
 if(login!==204)throw Error('browser login endpoint failed '+login);
 Object.assign(report,{browser_login_status:login,passed:true,host_rewritten:'fnconnect.internal',origin:'http://127.0.0.1:18083',settings_readback:true,slash_and_no_slash:true,resources,links});
 fs.writeFileSync('evidence/gateway-browser.json',JSON.stringify(report,null,2));console.log('Gateway browser HTML/JS/CSS/API/settings/prefix links passed');
} finally {await browser?.close();await new Promise(resolve=>server.close(resolve))}
