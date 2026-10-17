import {torrentActionConfirmed} from './pt';
import {hashesBody,parseTags,validateLabel} from './tags';
type Client=(path:string,body?:URLSearchParams)=>Promise<any>;
export type BatchAction='start'|'force'|'stop'|'labels'|'category'|'tags';
export type BatchResult={ok:string[];failed:string[]};
async function readOne(api:Client,hash:string){const list=await api(`torrents/info?hashes=${encodeURIComponent(hash)}`);if(!Array.isArray(list)||list.length!==1)throw Error('回读未找到任务；不自动重发');return list[0];}
export async function runBatch(api:Client,action:BatchAction,hashes:string[],category='',tags:string[]=[]):Promise<BatchResult>{
 hashesBody(hashes);const changeCategory=action==='category'||action==='labels',changeTags=action==='tags'||action==='labels';
 if(changeCategory&&category)validateLabel(category,'分类');if(changeTags)tags=[...new Set(tags.map(t=>validateLabel(t,'标签')))];
 const ok:string[]=[],failed:string[]=[];
 for(const hash of [...new Set(hashes)]){try{
  const before=await readOne(api,hash);
  if(changeCategory&&before.auto_tmm)throw Error('自动管理可能移动文件；已阻止分类变更');
  if(action==='start'){await api('torrents/setForceStart',new URLSearchParams({hashes:hash,value:'false'}));await api('torrents/start',new URLSearchParams({hashes:hash}));}
  else if(action==='force')await api('torrents/setForceStart',new URLSearchParams({hashes:hash,value:'true'}));
  else if(action==='stop')await api('torrents/stop',new URLSearchParams({hashes:hash}));
  else {
   if(changeCategory)await api('torrents/setCategory',new URLSearchParams({hashes:hash,category}));
   if(changeTags){const existing=parseTags(before.tags),remove=existing.filter(t=>!tags.includes(t)),add=tags.filter(t=>!existing.includes(t));if(remove.length)await api('torrents/removeTags',new URLSearchParams({hashes:hash,tags:remove.join(',')}));if(add.length)await api('torrents/addTags',new URLSearchParams({hashes:hash,tags:add.join(',')}));}
  }
  let confirmed=false;
  for(let attempt=0;attempt<12;attempt++){
   const after=await readOne(api,hash);
   confirmed=action==='stop'||action==='force'||action==='start'?torrentActionConfirmed(action,after):(!changeCategory||after.category===category)&&(!changeTags||JSON.stringify(parseTags(after.tags).sort())===JSON.stringify([...tags].sort()));
   if(confirmed)break;await new Promise(r=>setTimeout(r,150));
  }
  if(!confirmed)throw Error('读回状态不匹配');ok.push(hash);
 }catch(e){failed.push(`${hash.slice(0,8)}: ${(e as Error).message}`)}}
 return {ok,failed};
}
