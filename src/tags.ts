export type Category={name:string,savePath?:string};
export const MAX_LABEL_LENGTH=256;
export function validateLabel(value:string,kind='名称'){
 const s=value;
 if(kind==='标签'&&s.includes(','))throw Error('标签不能包含逗号：qB 标准接口将其用作分隔符');
 if(!s.trim())throw Error(`${kind}不能为空`);
 if([...s].length>MAX_LABEL_LENGTH)throw Error(`${kind}不能超过 ${MAX_LABEL_LENGTH} 个 Unicode 字符`);
 if([...s].some(c=>{const n=c.codePointAt(0)!;return n===0||n<0x20||n===0x7f}))throw Error(`${kind}不能包含控制字符、换行或 NUL`);
 return s;
}
export function parseTags(value:unknown):string[]{
 if(Array.isArray(value))return value.filter(x=>typeof x==='string');
 if(typeof value!=='string')return [];
 return value.split(',').map(x=>x.trim()).filter(Boolean);
}
export function labelBody(name:string){return new URLSearchParams({tags:validateLabel(name,'标签')})}
export function hashesBody(hashes:string[]){
 if(!hashes.length)throw Error('未选择任务');
 if(hashes.some(h=>!/^[a-fA-F0-9]{40,64}$/.test(h)))throw Error('任务 Hash 无效');
 return hashes.join('|');
}
export async function readLabelState(api:(path:string,body?:URLSearchParams)=>Promise<any>){
 const [categories,tags]=await Promise.all([api('torrents/categories'),api('torrents/tags')]);
 const categoryList:Category[]=Object.entries(categories&&typeof categories==='object'?categories:{}).map(([name,v])=>({name,savePath:typeof v==='object'&&v?String((v as any).savePath??''):''}));
 const tagList=Array.isArray(tags)?tags.filter(x=>typeof x==='string'):parseTags(tags);
 return {categories:categoryList,tags:tagList};
}
export async function setTorrentLabels(api:(path:string,body?:URLSearchParams)=>Promise<any>,hashes:string[],category:string,tags:string[]){
 const clean=tags.map(x=>validateLabel(x,'标签'));hashesBody(hashes);
 if(category)validateLabel(category,'分类');
 const results:any[]=[];const failed:string[]=[];
 for(const hash of hashes){
  try{
   const before=await api(`torrents/info?hashes=${encodeURIComponent(hash)}`);
   if(!Array.isArray(before)||before.length!==1)throw Error('任务不存在');
   if(before[0].auto_tmm)throw Error('自动管理任务可能移动文件，请先明确确认路径策略');
   await api('torrents/setCategory',new URLSearchParams({hashes:hash,category}));
   const existing=parseTags(before[0].tags),remove=existing.filter(x=>!clean.includes(x)),add=clean.filter(x=>!existing.includes(x));
   if(remove.length)await api('torrents/removeTags',new URLSearchParams({hashes:hash,tags:remove.join(',')}));
   if(add.length)await api('torrents/addTags',new URLSearchParams({hashes:hash,tags:add.join(',')}));
   const after=await api(`torrents/info?hashes=${encodeURIComponent(hash)}`);
   if(after.length!==1||after[0].category!==category||JSON.stringify(parseTags(after[0].tags).sort())!==JSON.stringify([...clean].sort()))throw Error('读回不匹配');
   results.push(after);
  }catch(e){failed.push(hash.slice(0,8)+': '+(e as Error).message)}
 }
 if(failed.length)throw Error(`批量未确认：已确认 ${results.length}，失败 ${failed.length}；${failed.join('；')}`);
 return results;
}
