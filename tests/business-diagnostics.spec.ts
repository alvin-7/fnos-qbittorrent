import {test,expect} from '@playwright/test';
const base='http://127.0.0.1:15173';
test('mock: default URL addition explicitly starts and reports observed state',async({page})=>{
 let added=false;let payload='';
 await page.route('**/api/v2/**',async r=>{const p=new URL(r.request().url()).pathname;if(p.endsWith('/add')){payload=r.request().postData()||'';added=true;return r.fulfill({body:'Ok.'})}return r.fulfill({json:added?[{hash:'a',name:'fixture',state:'metaDL',progress:0,size:0,eta:8640000}]:[]})});
 await page.goto(base);await page.getByRole('button',{name:'添加任务',exact:true}).click();
 await page.locator('[name=urls]').fill('https://example.invalid/rss?id=fixture&sign=REDACTED');await page.getByRole('button',{name:'开始添加',exact:true}).click();
 await expect.poll(()=>new URLSearchParams(payload).get('stopped')).toBe('false');
 expect(new URLSearchParams(payload).get('urls')).toBe('https://example.invalid/rss?id=fixture&sign=REDACTED');
 await expect(page.getByRole('status')).toContainText('获取元数据');
});

test('mock: detail shows real diagnostics without tracker secrets',async({page})=>{
 const t={hash:'abc',name:'fixture',state:'stalledDL',progress:0,num_seeds:2,num_complete:7,num_leechs:3,num_incomplete:9,dlspeed:0,upspeed:0,availability:0.5};
 await page.route('**/api/v2/**',r=>{const p=new URL(r.request().url()).pathname;return r.fulfill({json:p.endsWith('/properties')?{has_metadata:false,nb_connections:5,save_path:'/downloads',total_downloaded:12}:p.endsWith('/trackers')?[{url:'https://tracker.invalid/secret-passkey/announce?token=SECRET',status:4,msg:'failed https://tracker.invalid/secret-passkey?token=SECRET'}]:p.endsWith('/files')?[]:p.endsWith('/transfer/info')?{dht_nodes:0,connection_status:'firewalled'}:[t]})});
 await page.goto(base);await page.getByRole('button',{name:'详情 fixture',exact:true}).click();
 await expect(page.getByText('连接种子 / 总种子：2 / 7',{exact:true})).toBeVisible();await expect(page.getByText('元数据：等待获取（API 未提供百分比）',{exact:true})).toBeVisible();
 await page.getByText('Tracker 诊断',{exact:true}).click();await expect(page.getByRole('dialog')).toContainText('错误 (4)');expect(await page.getByRole('dialog').textContent()).not.toContain('SECRET');expect(await page.getByRole('dialog').textContent()).not.toContain('secret-passkey');
});

for(const [source,paused] of [['magnet:?dn=fixture&xt=urn:btih:0123456789012345678901234567890123456789',false],['http://example.invalid/rss?id=fixture&sign=REDACTED',true]] as const){test(`mock: preserves source and explicit pause ${paused}`,async({page})=>{
 let payload='';await page.route('**/api/v2/**',r=>{if(r.request().url().endsWith('/add')){payload=r.request().postData()||'';return r.fulfill({json:{pending_count:1}})}return r.fulfill({json:[]})});await page.goto(base);await page.getByRole('button',{name:'添加任务',exact:true}).click();await page.locator('[name=urls]').fill(source);if(paused)await page.getByLabel('添加后保持暂停').check();await page.getByRole('button',{name:'开始添加',exact:true}).click();await expect.poll(()=>new URLSearchParams(payload).get('stopped')).toBe(String(paused));expect(new URLSearchParams(payload).get('urls')).toBe(source);await expect(page.getByRole('status').filter({hasText:'暂未观察到新任务'})).toBeVisible();
})}
test('mock: file + URL share multipart parameters and preserve pause',async({page})=>{
 let payload='';await page.route('**/api/v2/**',r=>{if(r.request().url().endsWith('/add')){payload=r.request().postData()||'';return r.fulfill({json:{success_count:1}})}return r.fulfill({json:[]})});await page.goto(base);await page.getByRole('button',{name:'添加任务',exact:true}).click();await page.locator('[name=torrents]').setInputFiles('tests/fixtures/legal-test.torrent');await page.locator('[name=urls]').fill('https://example.invalid/query?id=fixture');await page.getByLabel('添加后保持暂停').check();await page.getByRole('button',{name:'开始添加',exact:true}).click();await expect.poll(()=>payload.includes('name="stopped"\r\n\r\ntrue')).toBe(true);expect(payload).toContain('https://example.invalid/query?id=fixture');expect(payload).toContain('name="torrents"');
});
