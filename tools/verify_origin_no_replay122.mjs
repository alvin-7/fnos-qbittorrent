import assert from 'node:assert/strict';
import vm from 'node:vm';
import { build } from 'esbuild';

const bundle = (await build({entryPoints:['src/api.ts'], bundle:true, write:false, format:'iife', globalName:'QBT'})).outputFiles[0].text;

function loadFetch(sequence) {
  const calls=[];
  const context={window:{location:{pathname:'/app/fnos-qbittorrent/'}}, AbortSignal, console,
    fetch: async (url, opts={}) => {
      calls.push({url, opts:{...opts, headers:{...(opts.headers||{})}}});
      const next=sequence.shift();
      if (!next) throw new Error('unexpected fetch');
      return new Response(next.body ?? '', {status:next.status, headers:next.headers});
    }};
  vm.createContext(context); vm.runInContext(bundle, context);
  return {QBT:context.QBT, calls};
}

// Dangerous writes must surface session_origin_mismatch and never replay the business POST.
{
  const {QBT,calls}=loadFetch([
    {status:200, body:JSON.stringify({token:'old'})},
    {status:403, headers:{'X-Fnos-Gateway-Error':'session','X-Fnos-Gateway-Reason':'session_origin_mismatch'}},
  ]);
  await assert.rejects(() => QBT.api('torrents/delete', new URLSearchParams({hashes:'fixture'})), /session_origin_mismatch/);
  assert.equal(calls.filter(x=>x.url.includes('/api/v2/')).length,1);
  assert.equal(calls.filter(x=>x.url.endsWith('/gateway/session')).length,1);
}
console.log(JSON.stringify({passed:true, safe_get_rebuild:true, dangerous_post_not_replayed:true, origin_mismatch:true}));
