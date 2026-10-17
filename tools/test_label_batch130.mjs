import ts from 'typescript';import fs from 'node:fs';import assert from 'node:assert/strict';
const source=ts.transpile(fs.readFileSync('src/tags.ts','utf8'),{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022});
const {setTorrentLabels}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const a='a'.repeat(40),b='b'.repeat(40);const tasks={[a]:{hash:a,category:'old',tags:'first'},[b]:{hash:b,category:'old',tags:''}};
const api=async(path,body)=>{if(path.startsWith('torrents/info?'))return tasks[decodeURIComponent(path.split('=')[1])]? [tasks[decodeURIComponent(path.split('=')[1])]]:[];for(const h of body.get('hashes').split('|')){const t=tasks[h];if(!t)continue;if(path.endsWith('setCategory'))t.category=body.get('category');if(path.endsWith('addTags'))t.tags=[...new Set([...t.tags.split(',').filter(Boolean),...body.get('tags').split(',')])].join(',');if(path.endsWith('removeTags'))t.tags=t.tags.split(',').filter(x=>!body.get('tags').split(',').includes(x)).join(',')}};
await setTorrentLabels(api,[a,b],'',['first']);assert.equal(tasks[a].category,'');assert.equal(tasks[b].category,'');assert.equal(tasks[b].tags,'first');
await assert.rejects(()=>setTorrentLabels(api,[a,'c'.repeat(40)],'',['first']),/未确认|不存在/);
console.log('all hashes independently read back; missing hash rejects; clear category supported');
