import {test,expect} from '@playwright/test';
const base=process.env.FIX_UI_URL||'http://127.0.0.1:18740';
const hash='a'.repeat(40),other='b'.repeat(40);
test('selection is cleared on search/filter/resource and pruned on refresh',async({page})=>{
 let tasks=[{hash,name:'alpha',state:'stoppedUP',progress:1,category:'one',tags:'tag'},{hash:other,name:'beta',state:'stoppedUP',progress:1,category:'two',tags:''}];let writes=0;
 await page.route('**/api/v2/**',r=>{const p=new URL(r.request().url()).pathname;if(r.request().method()==='POST')writes++;return r.fulfill({json:p.endsWith('/torrents/info')?tasks:p.endsWith('/torrents/categories')?{one:{name:'one',savePath:''},two:{name:'two',savePath:''}}:p.endsWith('/torrents/tags')?['tag']:[]})});
 await page.goto(base);await page.getByRole('button',{name:'选择',exact:true}).click();
 const select=()=>page.getByRole('checkbox',{name:'选择 alpha'}).check();
 await select();await page.getByRole('textbox',{name:'搜索任务名称'}).fill('beta');await expect(page.getByText('已选 1 项')).toHaveCount(0);
 await page.getByRole('textbox',{name:'搜索任务名称'}).fill('');await select();await page.getByRole('combobox',{name:'任务筛选'}).selectOption('complete');await expect(page.getByText('已选 1 项')).toHaveCount(0);
 await select();await page.locator('.resource-row').filter({hasText:'one'}).click();await expect(page.getByText('已选 1 项')).toHaveCount(0);await page.getByRole('button',{name:'返回资源',exact:true}).click();await select();tasks=tasks.filter(t=>t.hash!==hash);await expect(page.getByRole('checkbox',{name:'选择 alpha'})).toHaveCount(0,{timeout:6000});await expect(page.getByText('已选 1 项')).toHaveCount(0);expect(writes).toBe(0);
});
test('saved password hide immediately clears plaintext and cancels delayed reveal after leaving settings',async({page})=>{
 let reveals=0;page.on('dialog',d=>d.accept());
 await page.route('**/api/v2/**',async r=>{const p=new URL(r.request().url()).pathname;if(p.endsWith('/password/reveal')){reveals++;return r.fulfill({json:{password:'synthetic-reveal-fixture'}})}return r.fulfill({json:p.endsWith('/connector/status')?{enabled:false,port:18081,username:'fixture',passwordSet:true}:p.endsWith('/app/preferences')?{save_path:'/downloads',temp_path:'/downloads',listen_port:49160}:p.endsWith('/transfer/speedLimitsMode')?0:[]})});
 await page.goto(base);await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'高级设置',exact:true}).click();
 const input=page.getByLabel('MoviePilot 专用密码（新密码，不回填已保存密码）');await page.getByRole('button',{name:'显示 MoviePilot 专用密码'}).click();await expect(input).toHaveValue('synthetic-reveal-fixture');await page.getByRole('button',{name:'隐藏 MoviePilot 专用密码'}).click();await expect(input).toHaveValue('');await expect(input).toHaveAttribute('type','password');expect(reveals).toBe(1);
 await page.getByRole('button',{name:'显示 MoviePilot 专用密码'}).click();await page.getByRole('button',{name:'关闭设置'}).click();await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'高级设置',exact:true}).click();await expect(input).toHaveValue('');await expect(input).toHaveAttribute('type','password');
});
