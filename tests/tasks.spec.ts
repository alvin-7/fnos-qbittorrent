import {test,expect} from './real-fixture';import fs from 'node:fs';
export async function login(page:any){await page.goto('http://127.0.0.1:18080');await expect(page.getByRole('button',{name:'添加任务',exact:true})).toBeVisible()}
test('通过正式入口添加本地私有合法种子',async({page})=>{await login(page);await page.getByRole('button',{name:'添加任务',exact:true}).click();await page.getByLabel('种子文件').setInputFiles('tests/fixtures/legal-test.torrent');await page.getByRole('button',{name:'开始添加',exact:true}).click();await expect(page.getByText('legal-test.txt',{exact:true}).first()).toBeVisible();});
