import ts from 'typescript';import fs from 'node:fs';import assert from 'node:assert/strict';
const source=ts.transpile(fs.readFileSync('src/tags.ts','utf8'),{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022});
const m=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
assert.throws(()=>m.validateLabel('one,two','标签'),/逗号/);
assert.equal(m.validateLabel('e\u0301','标签'),'e\u0301');
console.log('comma rejected; Unicode identity preserved');
