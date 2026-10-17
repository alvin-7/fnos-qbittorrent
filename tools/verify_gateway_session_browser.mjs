// Browser security suite: transport is test-only, real Unix adapter + real qB.
import http from 'node:http';import fs from 'node:fs';import {chromium} from 'playwright';import {build} from 'esbuild';
const socket=process.argv[2],p='/app/fnos-qbittorrent',report={};
const bundle=(await build({entryPoints:['src/api.ts'],bundle:true,write:false,format:'iife',globalName:'QBT'})).outputFiles[0].text;
const server=http.createServer((req,res)=>{
 if(req.url==='/shell'){res.setHeader('Content-Type','text/html');return res.end(`<iframe src="${p}/test-page"></iframe>`)}
 if(req.url===p+'/test-page'){res.setHeader('Content-Type','text/html');return res.end(`<script>${bundle}</script>`)}
 const headers={...req.headers,host:'localhost','x-trim-userid':'1000','x-trim-isadmin':'true'};
 const u=http.request({socketPath:socket,path:req.url,method:req.method,headers},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)});u.on('error',()=>{res.writeHead(502);res.end()});req.pipe(u);
});
await new Promise(r=>server.listen(18083,'0.0.0.0',r));
const evil=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end('<h1>attacker</h1>')});await new Promise(r=>evil.listen(18084,'0.0.0.0',r));
let browser;try{
 browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--no-proxy-server','--host-resolver-rules=MAP arbitrary.example 127.0.0.1, MAP evil.example 127.0.0.1']});
 const context=await browser.newContext();const page=await context.newPage();
 for(const host of ['localhost','arbitrary.example']){
  const base=`http://${host}:18083`;await page.goto(base+'/shell');const frame=page.frames().find(f=>f.url().includes('/test-page'));
  const result=await frame.evaluate(async()=>{
   const versions=await Promise.all(Array.from({length:8},()=>QBT.api('app/version')));if(versions.some(v=>v!=='v5.2.4'))throw Error('version');
   const prefs=await QBT.api('app/preferences');if(!prefs.web_ui_csrf_protection_enabled||!prefs.web_ui_host_header_validation_enabled)throw Error('qB protections off');
   await QBT.api('app/setPreferences',new URLSearchParams({json:JSON.stringify({dl_limit:333824})}));if((await QBT.api('app/preferences')).dl_limit!==333824)throw Error('readback');
   const b=await fetch('/app/fnos-qbittorrent/gateway/session',{method:'POST',headers:{'X-Fnos-Bootstrap':'1'}});const {token}=await b.json();
   const checks={};for(const [name,headers,credentials] of [['missing-header',{},'same-origin'],['bad-token',{'X-Fnos-CSRF':'wrong'},'same-origin'],['missing-cookie',{'X-Fnos-CSRF':token},'omit']]){const r=await fetch('/app/fnos-qbittorrent/api/v2/app/setPreferences',{method:'POST',headers,credentials,body:new URLSearchParams({json:'{}'})});checks[name]=r.status;if(r.status!==403)throw Error(name)}
   await QBT.api('auth/logout',new URLSearchParams());await QBT.api('app/version');return {versions:versions.length,settings:true,checks,logout_rebootstrap:true};
  });report[host]=result;
 }
 await page.goto('http://evil.example:18084/');
 report.attacks=await page.evaluate(async()=>{
  const target='http://arbitrary.example:18083/app/fnos-qbittorrent';const results={};
  for(const [name,path,headers] of [['bootstrap','/gateway/session',{'X-Fnos-Bootstrap':'1'}],['forged-trim','/api/v2/app/setPreferences',{'X-Trim-Isadmin':'true','X-Trim-Userid':'1000'}]]){try{await fetch(target+path,{method:'POST',credentials:'include',headers,body:new URLSearchParams({json:'{}'})});results[name]='unexpected-success'}catch{results[name]='CORS-blocked'}}
  await new Promise(resolve=>{const f=document.createElement('iframe');f.name='attack';document.body.append(f);const form=document.createElement('form');form.method='POST';form.action=target+'/api/v2/app/setPreferences';form.target='attack';const input=document.createElement('input');input.name='json';input.value='{"dl_limit":999424}';form.append(input);document.body.append(form);f.onload=resolve;form.submit();setTimeout(resolve,1000)});results.form='submitted';return results;
 });
 if(Object.values(report.attacks).includes('unexpected-success'))throw Error('CORS open');
 await page.goto('http://arbitrary.example:18083'+p+'/test-page');const limit=await page.evaluate(async()=>(await QBT.api('app/preferences')).dl_limit);if(limit!==333824)throw Error('cross-site form mutated qB');report.cross_site_form_no_write=true;
 report.passed=true;fs.writeFileSync('evidence/gateway-session-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
}finally{await browser?.close();await new Promise(r=>server.close(r));await new Promise(r=>evil.close(r))}
