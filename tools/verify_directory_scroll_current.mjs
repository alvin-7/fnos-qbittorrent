import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',args:['--no-sandbox','--no-proxy-server']});
const report=[];
try{for(const width of [1440,390]){
 const page=await browser.newPage({viewport:{width,height:844},hasTouch:true});
 await page.route('**/api/v2/**',r=>{const path=r.request().url();let data=[];if(path.includes('app/preferences'))data={save_path:'/fixture/授权 空格',temp_path:'/fixture/授权 空格',temp_path_enabled:false};else if(path.includes('sync/maindata'))data={rid:1,full_update:true,torrents:{},categories:{},tags:[],server_state:{}};else if(path.includes('transfer/info'))data={};else if(path.includes('speedLimitsMode'))data=0;else if(path.includes('categories'))data={};r.fulfill({contentType:'application/json',body:JSON.stringify(data)})});
 const roots=[{rootId:'a',name:'授权 空格',canonicalPath:'/fixture/授权 空格',relativePath:'',writable:true},{rootId:'b',name:'qBittorrent',canonicalPath:'/fixture/vol2/qBittorrent',relativePath:'',writable:true},{rootId:'c',name:'qBittorrent',canonicalPath:'/fixture/vol3/qBittorrent',relativePath:'',writable:true},{rootId:'d',name:'xx',canonicalPath:'/fixture/vol2/alvin 的文件/xx',relativePath:'',writable:true}];
 await page.route('**/gateway/directories/**',r=>{const action=r.request().url().split('/').at(-1);const body=r.request().postDataJSON();const root=roots.find(x=>x.rootId===body.rootId)||roots[0];const data=action==='roots'?{roots,authorizationRevision:'fixture'}:action==='validate'?{...root,canonicalPath:body.manualPath||root.canonicalPath}:{entries:Array.from({length:70},(_,i)=>({...root,name:'目录 '+i,relativePath:'目录 '+i,canonicalPath:root.canonicalPath+'/目录 '+i})),nextCursor:'',canonicalPath:root.canonicalPath};return r.fulfill({contentType:'application/json',body:JSON.stringify(data)})});
 await page.goto('http://127.0.0.1:18192');await page.getByRole('heading',{name:'下载任务',exact:true}).waitFor();
 await page.evaluate(()=>{document.body.style.minHeight='2800px';window.scrollTo(0,320)});
 const original=await page.evaluate(()=>window.scrollY);assert.equal(original,320);
 // Programmatic DOM click avoids Playwright scrolling the background trigger into view.
 await page.getByRole('button',{name:'设置',exact:true}).first().evaluate(e=>e.click());
 const settings=page.getByRole('dialog',{name:'设置',exact:true});await settings.locator('[name=save_path]').waitFor();
 const locked=await page.evaluate(()=>window.scrollY);const bodyTop=await page.evaluate(()=>document.body.style.top);assert.equal(bodyTop,'-320px');
 await settings.getByRole('button',{name:'选择目录',exact:true}).first().click();
 const picker=page.getByRole('dialog',{name:'选择下载目录',exact:true});await picker.getByRole('button',{name:'刷新授权状态'}).waitFor();
 await picker.getByRole('button',{name:'已授权目录',exact:true}).click();
 await picker.locator(width===390?'.directory-layer-row':'.directory-name').filter({hasText:'授权 空格'}).first().click();
 const list=picker.locator('.directory-content');await list.locator(width===390?'.directory-layer-row':'.directory-name').last().waitFor();
 assert(await list.evaluate(e=>e.scrollHeight>e.clientHeight));
 const box=await list.boundingBox();const footer=await picker.locator('footer').boundingBox();const header=await picker.locator('header').boundingBox();
 await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.wheel(0,500);await page.waitForTimeout(300);
 assert(await list.evaluate(e=>e.scrollTop>0));assert.equal(await page.evaluate(()=>window.scrollY),locked);
 // Real Chromium touch input, not synthetic DOM events.
 await list.evaluate(e=>e.scrollTop=0);const session=await page.context().newCDPSession(page);
 const x=Math.round(box.x+box.width/2),y=Math.round(box.y+box.height-30);
 await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
 for(let i=1;i<=8;i++){await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x,y:y-i*18}]});await page.waitForTimeout(20)}
 await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await page.waitForTimeout(400);
 assert(await list.evaluate(e=>e.scrollTop>0),'touch must scroll picker');assert.equal(await page.evaluate(()=>window.scrollY),locked);
 await list.evaluate(e=>e.scrollTop=e.scrollHeight);await page.mouse.wheel(0,1200);await page.waitForTimeout(300);assert.equal(await page.evaluate(()=>window.scrollY),locked);
 assert.equal((await picker.locator('footer').boundingBox()).y,footer.y);assert.equal((await picker.locator('header').boundingBox()).y,header.y);
 assert(footer.y+footer.height<=844.5);assert(header.y>=0);
 await picker.getByRole('button',{name:'取消',exact:true}).click();assert.equal(await page.evaluate(()=>document.body.style.position),'fixed');assert.equal(await page.evaluate(()=>document.body.style.top),bodyTop);
 await settings.getByRole('button',{name:'关闭设置',exact:true}).click();await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>window.scrollY),original);assert.notEqual(await page.evaluate(()=>document.body.style.position),'fixed');
 report.push({width,wheel:true,touch:true,edge_containment:true,header_footer_fixed:true,nested_lock:true,original_scroll_restored:true,provider:'test-only route fixture; not NAS'});await page.close();
}fs.writeFileSync('evidence/directory-scroll-current.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));}finally{await browser.close()}
