import {test as base,expect} from '@playwright/test';import fs from 'node:fs';
export const test=base.extend<{realData:void}>({realData:[async({request,context},use,testInfo)=>{
 const url='http://127.0.0.1:18080/api/v2/';
 const login=await request.post(url+'auth/login',{form:{username:'admin',password:fs.readFileSync('.runtime/password','utf8').trim()}});expect(login.ok()).toBeTruthy();
 const old=await request.get(url+'torrents/info');const list=await old.json();if(list.length){const d=await request.post(url+'torrents/delete',{form:{hashes:list.map((x:any)=>x.hash).join('|'),deleteFiles:'false'}});expect(d.ok()).toBeTruthy()}
 if(!/login|tasks/.test(testInfo.file)){
 const add=await request.post(url+'torrents/add',{multipart:{torrents:{name:'legal-test.torrent',mimeType:'application/x-bittorrent',buffer:fs.readFileSync('tests/fixtures/legal-test.torrent')},savepath:'/downloads',stopped:'false'}});expect(add.ok()).toBeTruthy();
 await expect.poll(async()=>{const q=await request.get(url+'torrents/info');return (await q.json()).length}).toBe(1);
 }
 await context.addCookies((await request.storageState()).cookies);
 await use();
 },{auto:true}]});export {expect};
