import ts from 'typescript';import fs from 'node:fs';import assert from 'node:assert/strict';
const moduleURL=(file)=>'data:text/javascript;base64,'+Buffer.from(ts.transpile(fs.readFileSync(file,'utf8'),{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022})).toString('base64');
const tags=moduleURL('src/tags.ts'),pt=moduleURL('src/pt.ts');
const source=ts.transpile(fs.readFileSync('src/batch.ts','utf8'),{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}).replaceAll("'./tags'",JSON.stringify(tags)).replaceAll("'./pt'",JSON.stringify(pt));
const {runBatch}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const hash='a'.repeat(40);let reads=0,writes=0;
const api=async(p,b)=>{if(b){writes++;return}reads++;return [{hash,state:reads<4?'stoppedUP':'forcedUP',force_start:true}]};
const r=await runBatch(api,'force',[hash]);assert.deepEqual(r.ok,[hash]);assert.ok(reads>=4,'force must await non-paused state, not just force=true');assert.equal(writes,1);
console.log('PASS batch force waits out stoppedUP+force=true; one mutation, read-only convergence');
