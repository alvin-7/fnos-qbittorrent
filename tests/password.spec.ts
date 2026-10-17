import {test,expect} from './real-fixture';
test('认证提示不提供密码修改入口',async({page})=>{await page.goto('http://127.0.0.1:18080');await page.getByRole('button',{name:'设置',exact:true}).click();await expect(page.getByText('方案A：可信局域网免密码。')).toHaveCount(0);await expect(page.getByText('更改登录账号与密码')).toHaveCount(0);});
