"""Exercise final 1.2.4 packaged bytes with isolated native1.1.9 real regressions."""
from pathlib import Path
import subprocess, os
R=Path(__file__).resolve().parents[1]
D=R/'.runtime/regression124';D.mkdir(exist_ok=True)
for name in ['verify_pt119_real.py','verify_pt119_browser.mjs','verify_diagnostics119_real.py','verify_diagnostics119_browser.mjs']:
    s=(R/'tools'/name).read_text().replace('.runtime/package119','.runtime/package124')
    # Keep original fixture ports and mechanics; never replace immutable prior evidence.
    s=s.replace('.runtime/pt119','.runtime/pt124').replace('.runtime/diagnostics119','.runtime/diagnostics124')
    s=s.replace('evidence/pt119','evidence/pt124').replace('evidence/diagnostics119','evidence/diagnostics124')
    if name.endswith('.py'):
        s=s.replace("R=pathlib.Path(__file__).resolve().parents[1]",'R=pathlib.Path('+repr(str(R))+')')
        s=s.replace('tools/verify_pt119_browser.mjs','.runtime/regression124/verify_pt119_browser.mjs').replace('tools/verify_diagnostics119_browser.mjs','.runtime/regression124/verify_diagnostics119_browser.mjs')
    s=s.replace('const u=http.request({socketPath:', "for(const k of Object.keys(req.headers))if(k.toLowerCase().startsWith('x-trim-'))delete req.headers[k];delete req.headers.cookie;const u=http.request({socketPath:") if name.endswith('.mjs') else s
    (D/name).write_text(s)
# Add final-package responsive/touch/overlay evidence to existing real fixture.
p=D/'verify_pt119_browser.mjs'
s=p.read_text()
s=s.replace("const page=await browser.newPage();", "const page=await browser.newPage({hasTouch:true});")
s=s.replace("await page.setViewportSize(viewport);", "await page.setViewportSize(viewport);await verifyUI(f,page,task,viewport);")
s=s.replace("const pre=await qb('app/preferences');", "const pre=await qb('app/preferences');await f.locator('[name=listen_port]').fill(viewport.width===390?'49244':'49243');")
s=s.replace("const post=await qb('app/preferences');", "const post=await qb('app/preferences');assert.equal(post.listen_port,viewport.width===390?49244:49243);")
s=s.replace("await f.getByRole('button',{name:'关闭设置'}).click();report.cases.push", "await page.screenshot({path:'evidence/ui124-settings-'+viewport.width+'.png'});await f.getByRole('button',{name:'关闭设置'}).click();report.cases.push")
s += '''
async function verifyUI(f,page,task,v){
 await task.waitFor();await page.screenshot({path:'evidence/ui124-overview-'+v.width+'.png',fullPage:true});
 assert.equal(await f.title(),'飞牛 PT 下载');
 assert(await f.locator('.brand img').evaluate(e=>e.complete&&e.naturalWidth>0));
 assert(await f.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 const button=task.getByRole('button',{name:'开始',exact:true});
 const css=await button.evaluate(e=>{const s=getComputedStyle(e);return {highlight:s.webkitTapHighlightColor,touch:s.touchAction,transition:s.transitionDuration}});
 assert.equal(css.highlight,'rgba(0, 0, 0, 0)');assert.equal(css.touch,'manipulation');assert.equal(css.transition,'0s');
 for(const [open,dialog] of [['设置','设置'],['详情','任务详情']]){
  if(open==='详情')await task.getByRole('button',{name:/详情/}).click();else await f.getByRole('button',{name:open,exact:true}).click();
  const d=f.getByRole('dialog',{name:dialog,exact:true});await d.waitFor();await d.locator('h2').click();assert(await d.isVisible());
  if(open==='详情'){await d.getByText('文件列表',{exact:true}).waitFor();await page.screenshot({path:'evidence/ui124-detail-'+v.width+'.png'});}
  await f.locator('.overlay:visible').click({position:{x:2,y:2}});await d.waitFor({state:'hidden'});
 }
}
'''
p.write_text(s)
for name in ['verify_pt119_real.py','verify_diagnostics119_real.py']:
    subprocess.run(['python3',str(D/name)],cwd=R,check=True)
