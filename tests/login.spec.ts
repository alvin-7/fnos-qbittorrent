import {test,expect} from './real-fixture';
test('本机回环入口免密码进入自定义任务入口', async ({page})=>{await page.goto('http://127.0.0.1:18080');await expect(page.getByRole('button',{name:'添加任务',exact:true})).toBeVisible();await expect(page.getByRole('heading',{name:'轻下载'})).toHaveCount(0);});
