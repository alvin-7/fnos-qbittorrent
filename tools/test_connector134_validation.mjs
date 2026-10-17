import fs from 'node:fs';import assert from 'node:assert/strict';import ts from 'typescript';
const s=fs.readFileSync('src/connectorValidation.ts','utf8');const js=ts.transpile(s,{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ES2022});const {connectorValidation}=await import('data:text/javascript;base64,'+Buffer.from(js).toString('base64'));
assert.equal(connectorValidation({enabled:true,port:18081,username:'fixture',password:'fixture-password'}),'');
assert.match(connectorValidation({enabled:true,port:18081,username:'fixture',password:''}),/密码/);
for(const port of [18080,49160,0])assert.notEqual(connectorValidation({enabled:true,port,username:'fixture',password:'fixture'}),'');
console.log('LAN validation passed');
