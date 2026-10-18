import fs from 'node:fs';import assert from 'node:assert/strict';import vm from 'node:vm';import {transformSync} from 'esbuild';import {execFileSync} from 'node:child_process';
const source=process.env.FILTER_SOURCE?fs.readFileSync(process.env.FILTER_SOURCE,'utf8'):fs.readFileSync('src/main.tsx','utf8');
const start=source.indexOf('export type TaskFilter');const end=source.indexOf('function Login',start);
assert(start>=0,'filter export required');const code=transformSync(source.slice(start,end).replace(/export /g,''),{loader:'ts'}).code;
const context=vm.createContext({stopped:t=>/^(stopped|paused)/.test(t.state)});vm.runInContext(code,context);
const all=['downloading','stalledDL','forcedDL','queuedDL','metaDL','forcedMetaDL','uploading','stalledUP','forcedUP','queuedUP','stoppedUP','stoppedDL','pausedUP','pausedDL','error','missingFiles','checkingUP','moving'].map((state,i)=>({hash:String(i),name:'Task '+i,state,progress:state.endsWith('UP')?1:0,category:i%2?'Film':'TV',tags:i%2?'PT':'Archive'}));
const filter=(status='all',label={kind:'',value:''},siteHashes=null,query='')=>context.filterTorrents(all,{status,label,siteHashes,query});
assert.equal(filter('seeding').length,4,'only real seeding states, including queuedUP');assert.equal(filter('downloading').length,6);assert.equal(filter('stopped').length,4);assert.equal(filter('error').length,2);
assert.equal(filter().length,all.length);assert.equal(filter('all',undefined,[]).length,0,'active empty site is not inactive');assert.equal(filter('all',undefined,null).length,all.length);
assert.equal(filter('all',{kind:'category',value:'Film'},['1','3']).length,2);assert.equal(filter('all',{kind:'',value:''},null).length,all.length);assert.equal(filter('all',{kind:'tag',value:'PT'},null,'Task 1').length,5);console.log('PASS state semantics, null/empty site, combined removal');
if(!process.env.FILTER_SOURCE){const nav=source.match(/aria-label="任务状态"/g)||[];assert.equal(nav.length,1,'one top status navigation');assert(!source.includes('aria-label="移动任务筛选"'));assert(!source.includes('aria-label="任务筛选"'));console.log('PASS single navigation contract');}
