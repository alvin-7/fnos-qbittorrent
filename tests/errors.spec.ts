import {test,expect} from './real-fixture';
test('本机回环免密码入口在浏览器中可直接使用',async({page})=>{await page.goto('http://127.0.0.1:18080');await expect(page.getByRole('button',{name:'设置',exact:true})).toBeVisible();});
