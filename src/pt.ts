export function torrentActionConfirmed(action:'start'|'force'|'stop', t:{state:string,force_start?:boolean}){
 const paused=/^(stopped|paused)/.test(t.state);
 return action==='stop'?paused&&!t.force_start:action==='force'?t.force_start===true&&!paused:t.force_start===false&&!paused;
}
type Client=(path:string,body?:URLSearchParams)=>Promise<any>;
export async function runTorrentAction(api:Client,action:'start'|'force'|'stop',hash:string){
 if(!/^[a-fA-F0-9]{40,64}$/.test(hash))throw Error('无效任务 Hash');
 // setForceStart(false) itself starts AutoManaged; never call it after stop.
 if(action==='start'){await api('torrents/setForceStart',new URLSearchParams({hashes:hash,value:'false'}));await api('torrents/start',new URLSearchParams({hashes:hash}));}
 else if(action==='force')await api('torrents/setForceStart',new URLSearchParams({hashes:hash,value:'true'}));
 else await api('torrents/stop',new URLSearchParams({hashes:hash}));
 let t:any;
 for(let i=0;i<12;i++){
  const list=await api('torrents/info?hashes='+hash);t=list.find((x:any)=>x.hash===hash);
  if(!t)throw Error('回读未找到任务；不自动重发');
  if(torrentActionConfirmed(action,t))return t;
  await new Promise(r=>setTimeout(r,250));
 }
 throw Error(`请求已送达，但尚未确认目标状态（${t?.state}；force=${t?.force_start}）；未自动重发，请检查分享限制、队列和详情`);
}
export function shareRatioValues(d:{get:(k:string)=>unknown,has:(k:string)=>boolean}){
 const enabled=d.has('max_ratio_enabled');
 const raw=String(d.get('max_ratio')??'');
 const ratio=Number(raw);
 if(enabled&&(!/^\d+(?:\.\d+)?$/.test(raw)||!Number.isFinite(ratio)||ratio<=0||ratio>9999))throw Error('分享率阈值必须是大于 0 且不超过 9999 的数值');
 // qB 5.2.4 normalizes disabled global ratio to -1, not the previous threshold.
 if(!enabled)return {max_ratio_enabled:false,max_ratio:-1,max_ratio_act:0};
 return {max_ratio_enabled:true,max_ratio:ratio,max_ratio_act:0};
}
export function speedValues(d:{get:(k:string)=>unknown,has:(k:string)=>boolean}){
 const integer=(key:string,max:number)=>{const s=String(d.get(key)??'');if(!/^\d+$/.test(s)||!Number.isSafeInteger(Number(s))||Number(s)>max)throw Error('限速/日期必须为范围内非负整数：'+key);return Number(s)};
 const time=(key:string)=>{const s=String(d.get(key)??'');if(!/^([01]\d|2[0-3]):[0-5]\d$/.test(s))throw Error('时间必须为 HH:mm');return s.split(':').map(Number)};
 const from=time('schedule_from'),to=time('schedule_to');
 if(from[0]===to[0]&&from[1]===to[1])throw Error('起止时间不能相同');
 if((from[0]*60+from[1])>(to[0]*60+to[1])&&integer('scheduler_days',9)!==0)throw Error('跨午夜暂仅支持每天；非每日跨午夜语义特殊，未开放');
 return {dl_limit:integer('dl_limit',2097151)*1024,up_limit:integer('up_limit',2097151)*1024,alt_dl_limit:integer('alt_dl_limit',2097151)*1024,alt_up_limit:integer('alt_up_limit',2097151)*1024,schedule_from_hour:from[0],schedule_from_min:from[1],schedule_to_hour:to[0],schedule_to_min:to[1],scheduler_days:integer('scheduler_days',9),scheduler_enabled:d.has('scheduler_enabled')};
}
