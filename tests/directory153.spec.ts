import {test,expect} from '@playwright/test';
for(const width of [1440,390])for(const code of ['AUTH_SCOPE_DENIED','AUTH_USER_ACL_DENIED','AUTH_PACKAGE_READ_DENIED','AUTH_MOUNT_UNAVAILABLE','AUTH_MOUNT_REJECTED','AUTH_ROOTS_INACCESSIBLE'])test(`packaged directory fixed reason ${code} ${width}`,async({page})=>{
 await page.setViewportSize({width,height:844});let writes=0;
 await page.route('**/api/v2/**',r=>{if(r.request().method()==='POST')writes++;const p=r.request().url();return r.fulfill({json:p.includes('preferences')?{save_path:'/fixture/root'}:p.includes('torrents/info')?[]:{}})});
 await page.route('**/gateway/directories/**',r=>r.fulfill({status:503,json:{code,msg:'/secret/raw-platform-secret',diagnostics:{stage:'user_acl',counts:{discovered:4,aclErrors:1}}}}));
 await page.goto('http://127.0.0.1:15173');await page.getByRole('button',{name:'设置',exact:true}).first().click();const settings=page.getByRole('dialog',{name:'设置',exact:true});await settings.locator('[name=save_path]').waitFor();await settings.getByRole('button',{name:'选择目录',exact:true}).first().click();const picker=page.getByRole('dialog',{name:'选择下载目录',exact:true});await expect(picker.getByRole('alert')).toContainText(code);await expect(picker.getByRole('button',{name:'使用此目录',exact:true})).toBeDisabled();await expect(picker).not.toContainText('raw-platform-secret');expect(writes).toBe(0);
});
