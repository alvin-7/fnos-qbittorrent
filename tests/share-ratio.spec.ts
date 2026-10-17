import {test,expect} from '@playwright/test';

test('高级设置显示qB 5.2.4分享率控制并提交正确枚举',async({page})=>{
 const prefs:any={dht:false,pex:false,lsd:false,upnp:false,queueing_enabled:true,max_connec:100,dl_limit:0,up_limit:0,alt_dl_limit:0,alt_up_limit:0,schedule_from_hour:8,schedule_from_min:0,schedule_to_hour:20,schedule_to_min:0,scheduler_days:0,scheduler_enabled:false,max_ratio_enabled:false,max_ratio:-1,max_ratio_act:0,listen_port:49160,random_port:false,save_path:'/downloads',temp_path:'/downloads'};
 let posted:any;
 await page.route('**/api/v2/**',async r=>{
  const u=new URL(r.request().url()), p=u.pathname;
  if(p.endsWith('/app/preferences')) return r.fulfill({json:prefs});
  if(p.endsWith('/transfer/speedLimitsMode')) return r.fulfill({body:'0'});
  if(p.endsWith('/app/setPreferences')) {posted=JSON.parse(new URLSearchParams(r.request().postData()||'').get('json')||'{}');Object.assign(prefs,posted);return r.fulfill({status:200,body:''})}
  if(p.endsWith('/torrents/info')) return r.fulfill({json:[]});
  return r.fulfill({json:{}});
 });
 await page.goto('http://127.0.0.1:15173');
 await page.getByRole('button',{name:'设置',exact:true}).click();
 await page.getByRole('button',{name:'高级设置',exact:true}).click();
 await expect(page.getByLabel('启用分享率控制')).toBeVisible();
 await expect(page.getByLabel('分享率阈值（上传 / 下载）')).toHaveValue('0.1');
 await page.getByLabel('启用分享率控制').check();
 await page.getByLabel('分享率阈值（上传 / 下载）').fill('0.1');
 await page.getByRole('button',{name:'保存设置',exact:true}).click();
 await expect(page.getByText('设置已保存并核验')).toBeVisible();
 expect(posted.max_ratio_enabled).toBe(true); expect(posted.max_ratio).toBe(0.1); expect(posted.max_ratio_act).toBe(0);
});

for(const normalized of [-1,0.1]) test(`关闭分享率接受qB归一值 ${normalized} 并明确关闭状态`,async({page})=>{
 const prefs:any={dht:false,pex:false,lsd:false,upnp:false,queueing_enabled:true,max_connec:100,dl_limit:0,up_limit:0,alt_dl_limit:0,alt_up_limit:0,schedule_from_hour:8,schedule_from_min:0,schedule_to_hour:20,schedule_to_min:0,scheduler_days:0,scheduler_enabled:false,max_ratio_enabled:true,max_ratio:0.1,max_ratio_act:0};let posted:any;
 await page.route('**/api/v2/**',async r=>{const p=new URL(r.request().url()).pathname;if(p.endsWith('/app/preferences'))return r.fulfill({json:prefs});if(p.endsWith('/transfer/speedLimitsMode'))return r.fulfill({body:'0'});if(p.endsWith('/app/setPreferences')){posted=JSON.parse(new URLSearchParams(r.request().postData()||'').get('json')!);Object.assign(prefs,posted,{max_ratio:normalized});return r.fulfill({status:200,body:''})}if(p.endsWith('/torrents/info'))return r.fulfill({json:[]});return r.fulfill({json:{}})});
 await page.goto('http://127.0.0.1:15173');await page.getByRole('button',{name:'设置',exact:true}).click();await page.getByRole('button',{name:'高级设置',exact:true}).click();await page.getByLabel('启用分享率控制').uncheck();await page.getByRole('button',{name:'保存设置',exact:true}).click();await expect(page.getByText('设置已保存并核验',{exact:true})).toBeVisible();await expect(page.getByText('已关闭，qB将不自动因分享率停止',{exact:true})).toBeVisible();expect(posted.max_ratio_enabled).toBe(false);expect(posted.max_ratio).toBe(-1);expect(posted.max_ratio_act).toBe(0);await expect(page.getByRole('alert')).toHaveCount(0);
});

for(const value of ['0','-1','abc','10000']) for(const width of [1440,390]) test(`分享率非法值 ${value} 在 ${width}px 显示明确警告且零写入`,async({page})=>{
 await page.setViewportSize({width,height:844});
 const prefs:any={dht:false,pex:false,lsd:false,upnp:false,queueing_enabled:true,max_connec:100,dl_limit:0,up_limit:0,alt_dl_limit:0,alt_up_limit:0,schedule_from_hour:8,schedule_from_min:0,schedule_to_hour:20,schedule_to_min:0,scheduler_days:0,scheduler_enabled:false,max_ratio_enabled:true,max_ratio:0.1,max_ratio_act:0}; let writes=0;
 await page.route('**/api/v2/**',async r=>{const p=new URL(r.request().url()).pathname;if(p.endsWith('/app/preferences'))return r.fulfill({json:prefs});if(p.endsWith('/transfer/speedLimitsMode'))return r.fulfill({body:'0'});if(p.endsWith('/app/setPreferences')){writes++;return r.fulfill({status:200,body:''})}if(p.endsWith('/torrents/info'))return r.fulfill({json:[]});return r.fulfill({json:{}})});
 await page.goto('http://127.0.0.1:15173'); await page.getByRole('button',{name:'设置',exact:true}).click(); await page.getByRole('button',{name:'高级设置',exact:true}).click();
 const input=page.getByLabel('分享率阈值（上传 / 下载）');
 await input.fill(value);await expect(input).toHaveValue(value);
 await page.getByRole('button',{name:'保存设置',exact:true}).click();
 const alert=page.getByRole('alert');await expect(alert).toContainText('分享率阈值必须是大于 0 且不超过 9999 的数值');await expect(alert).toBeVisible();await expect(alert).toBeInViewport();
 await page.waitForTimeout(300);
 expect(writes).toBe(0);
});
