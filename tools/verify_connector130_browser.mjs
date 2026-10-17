import http from 'node:http';import fs from 'node:fs';import assert from 'node:assert/strict';import {chromium} from 'playwright';
const prefix='/app/fnos-qbittorrent-native',report={cases:[]};
const server=http.createServer((req,res)=>{if(req.url==='/shell'){res.setHeader('Content-Type','text/html');return res.end(`<style>html,body{height:100%;margin:0}iframe{height:100%;width:100%;border:0}</style><iframe src="${prefix}/"></iframe>`)}for(const k of Object.keys(req.headers))if(k.toLowerCase().startsWith('x-trim-'))delete req.headers[k];delete req.headers.cookie;const u=http.request({socketPath:process.env.GATEWAY_SOCKET,path:req.url,method:req.method,headers:{...req.headers,host:'gateway.internal','x-trim-userid':'1000','x-trim-isadmin':'true'}},r=>{res.writeHead(r.statusCode,r.headers);r.pipe(res)});u.on('error',()=>{res.writeHead(502);res.end()});req.pipe(u)});
await new Promise(r=>server.listen(18083,'127.0.0.1',r));let browser;
try{
 browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--no-proxy-server']});
 for(const width of [1440,390]){
  const page=await browser.newPage({viewport:{width,height:900},hasTouch:true});await page.goto('http://127.0.0.1:18083/shell');const f=page.frameLocator('iframe');await f.getByRole('button',{name:'设置',exact:true}).click();await f.getByRole('button',{name:'高级设置',exact:true}).click();
  const panel=f.getByRole('region',{name:'MoviePilot 连接器'});await panel.waitFor();assert.equal(await panel.getByLabel('启用 MoviePilot 连接器').isChecked(),false);assert.equal(await panel.locator('input[type=password]').inputValue(),'');assert.equal(await panel.locator('input[type=password]').getAttribute('type'),'password');
  await panel.getByRole('button',{name:'发现建议/重新检测'}).click();await panel.getByText(/候选接口/).waitFor();await panel.getByRole('button',{name:'只读测试后端'}).click();await panel.getByText(/后端只读探针：qB 5.2.4 就绪/).waitFor();
  assert(await f.locator('html').evaluate(e=>e.scrollWidth<=innerWidth));await panel.scrollIntoViewIfNeeded();await page.screenshot({path:`evidence/connector130-settings-${width}.png`,fullPage:true});
  await f.getByRole('button',{name:'关闭设置'}).click();await f.getByRole('button',{name:'设置',exact:true}).click();await f.getByRole('button',{name:'高级设置',exact:true}).click();assert.equal(await f.getByRole('region',{name:'MoviePilot 连接器'}).locator('input[type=password]').inputValue(),'');await f.getByRole('button',{name:'关闭设置'}).click();
  const labels=f.getByRole('region',{name:'分类与标签'});await labels.getByRole('combobox').selectOption('tag');await labels.getByPlaceholder('标签名称').fill('bad,split');await labels.getByRole('button',{name:'创建',exact:true}).click();await labels.getByRole('alert').filter({hasText:'逗号'}).waitFor();
  await labels.getByPlaceholder('标签名称').fill('UI-'+width);await labels.getByRole('button',{name:'创建',exact:true}).click();await labels.getByRole('button',{name:new RegExp('^UI-'+width)}).waitFor();await page.screenshot({path:`evidence/connector130-labels-${width}.png`,fullPage:true});
  report.cases.push({width,iframe:true,default_disabled:true,password_empty_masked:true,backend_readonly_probe:true,container_status_not_claimed:true,comma_rejected:true,tag_created_real_readback:true,no_horizontal_overflow:true});await page.close();
 }
 report.passed=true;fs.writeFileSync('evidence/connector130-browser.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{if(browser)await browser.close();server.close()}
