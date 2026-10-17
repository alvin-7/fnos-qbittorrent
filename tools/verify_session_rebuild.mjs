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

// Safe GET may rebuild the session exactly once, then retry the GET.
{
  const {QBT,calls}=loadFetch([
    {status:200, body:JSON.stringify({token:'old'})},
    {status:403, headers:{'X-Fnos-Gateway-Error':'session','X-Fnos-Gateway-Reason':'session_expired'}},
    {status:200, body:JSON.stringify({token:'new'})},
    {status:200, body:'"v5.2.4"'},
  ]);
  const result=await QBT.api('app/version');
  assert.equal(result,'v5.2.4');
  assert.deepEqual(calls.map(x=>x.url),[
    '/app/fnos-qbittorrent/gateway/session','/app/fnos-qbittorrent/api/v2/app/version',
    '/app/fnos-qbittorrent/gateway/session','/app/fnos-qbittorrent/api/v2/app/version']);
}

// Dangerous writes must surface session_expired and never replay the business POST.
{
  const {QBT,calls}=loadFetch([
    {status:200, body:JSON.stringify({token:'old'})},
    {status:403, headers:{'X-Fnos-Gateway-Error':'session','X-Fnos-Gateway-Reason':'session_expired'}},
  ]);
  await assert.rejects(() => QBT.api('torrents/delete', new URLSearchParams({hashes:'fixture'})), /session_expired/);
  assert.equal(calls.filter(x=>x.url.includes('/api/v2/')).length,1);
  assert.equal(calls.filter(x=>x.url.endsWith('/gateway/session')).length,1);
}
console.log(JSON.stringify({passed:true, safe_get_rebuild:true, dangerous_post_not_replayed:true}));
