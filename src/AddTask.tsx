import {useEffect,useRef,useState} from 'react';
import {api} from './main';
import {DirectoryButton} from './DownloadDirectoryPicker';
import {usePageScrollLock} from './usePageScrollLock';
import {stateName,redact,type Torrent} from './TorrentList';
import {validateLabel} from './tags';
export function validSource(value:string){try{const u=new URL(value);return (u.protocol==='http:'||u.protocol==='https:')?!!u.hostname:u.protocol==='magnet:'&&u.searchParams.getAll('xt').some(x=>/^urn:bt(?:ih:[a-z0-9]+|mh:[a-f0-9]+)$/i.test(x))}catch{return false}}
export function additionPayload(data:FormData){
 const paused=data.has('stopped');const urls=String(data.get('urls')||'').trim();
 const files=data.getAll('torrents').filter(x=>x instanceof File&&x.size>0);
 if(!urls&&!files.length)throw Error('请选择种子文件或输入磁力链接或 BT 链接');
 if(urls&&!urls.split(/\s+/).every(validSource))throw Error('请输入有效的磁力链接或 BT 下载链接（HTTP/HTTPS，仅使用可信来源）');
 const savepath=String(data.get('savepath')||'').trim();
 if(!savepath.startsWith('/')||/[\r\n\0]/.test(savepath))throw Error('保存位置必须是 NAS 上的绝对目录（以 / 开头），请确认应用有写入权限');
 const category=String(data.get('category')||'').trim();
 const tags=String(data.get('tags')||'').trim();
 if(category)validateLabel(category,'分类');
 if(tags)tags.split(',').map(x=>validateLabel(x.trim(),'标签'));
 const fields:any={urls,stopped:String(paused),savepath};
 if(category)fields.category=category;
 if(tags)fields.tags=tags;
 if(!files.length)return new URLSearchParams(fields);
 const body=new FormData();for(const [k,v] of Object.entries(fields))body.set(k,String(v));for(const file of files)body.append('torrents',file);return body;
}
export function AddTask({close,done,open=true}:{close:()=>void,done:()=>Promise<void>,open?:boolean}){
 usePageScrollLock(open);
 const native=(import.meta as any).env.VITE_NATIVE==='1';
 const [savepath,setSavepath]=useState(native?'':'/downloads'),edited=useRef(false),sending=useRef(false),alive=useRef(true);
 const recent=useRef<{before:string[],cursor:string,at:number}|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState(''),[stage,setStage]=useState(native?'正在读取默认保存位置…':''),[diagnostic,setDiagnostic]=useState(''),[hasRecent,setHasRecent]=useState(false);
 useEffect(()=>{alive.current=true;return()=>{alive.current=false}},[]);
 useEffect(()=>{let active=true;if(native)void api('app/preferences').then(p=>{if(!active||edited.current)return;if(typeof p.save_path==='string'&&p.save_path.trim()){setSavepath(p.save_path);setStage('')}else{setStage('');setError('未获得默认保存位置，请填写 NAS 上有写入权限的绝对目录后再添加。')}}).catch(e=>{if(active){setStage('');setError('读取默认保存位置失败：'+redact(e.message)+'；可手动填写目录。')}});return()=>{active=false}},[]);
 // Serial, bounded observation. Only GETs; never replay the accepted business POST.
 async function observe(manual=false){
  const r=recent.current;if(!r)return;
  const deadline=Date.now()+(native?45000:3000);
  do{
   if(!alive.current)return;
   try{
    const after:Torrent[]=await api('torrents/info');if(!Array.isArray(after))throw Error('任务列表响应格式异常');
    if(!alive.current)return;
    const added=after.filter(t=>!r.before.includes(t.hash));
    if(added.length){setResult('观察到新任务：'+added.map(t=>`${stateName(t)} (${t.state})`).join('；')+'；新增 hash 已确认，未证明下载完成。');setDiagnostic('实际任务已出现；此前时段错误不证明与本次请求相关。');await done();return}
   }catch{if(alive.current)setDiagnostic('任务查询暂不可用；结果未知，未自动重试提交。')}
   if(native&&r.cursor){
    try{
     const d=await api('diagnostics/add?cursor='+encodeURIComponent(r.cursor));if(!alive.current)return;
     if(d.status==='unknown'){setDiagnostic('诊断窗口已失效或诊断不可用，状态未知；保留最近结果，未自动重试。');return}
     const events=Array.isArray(d.events)?d.events:[];
     if(events.length){setError(events.map((x:any)=>x.code==='BENCODE_PARSE_ERROR'&&x.numeric_code===4?'INVALID_TORRENT [BENCODE_PARSE_ERROR] 返回内容不是有效种子（bdecode:4），可能为站点错误响应，具体响应未知（该时段后台错误，关联未确认）':`${redact(String(x.category))} [${redact(String(x.code))}] ${redact(String(x.message))}（该时段后台错误，关联未确认）`).join('；'));setResult('后台出现错误，未观察到新增 hash；不能确认添加或下载成功。未自动重试。');setDiagnostic('已读取增量诊断；可手动刷新诊断。');await done();return}
     setDiagnostic('未发现可用增量错误；无日志不代表成功。');
    }catch{if(alive.current)setDiagnostic('诊断暂不可用，状态未知；未自动重试提交。')}
   }
   if(manual||Date.now()>=deadline)break;
   await new Promise(r=>setTimeout(r,native?1000:600));
  }while(alive.current);
  if(alive.current){setResult('qB 已接受请求，暂未观察到新任务；限时观察结束，仍待确认。勿重复提交，可手动刷新诊断。');await done()}
 }
 async function refreshDiagnostics(){if(sending.current)return;sending.current=true;setBusy(true);setStage('正在刷新实际任务与增量诊断（不重新提交）…');try{await observe(true)}finally{sending.current=false;if(alive.current){setBusy(false);setStage('')}}}
 return <div className="overlay" style={{display:open?undefined:'none'}} aria-hidden={!open} onClick={e=>{if(e.target===e.currentTarget)close()}}><section role="dialog" aria-modal="true" aria-label="添加任务" aria-busy={busy} className="modal persistent-close"><form noValidate onSubmit={async e=>{e.preventDefault();if(sending.current)return;setError('');setResult('');setDiagnostic('');let sent=false;try{
 const payload=additionPayload(new FormData(e.currentTarget));sending.current=true;setBusy(true);setStage('正在核验现有任务（尚未提交）…');
 const before:Torrent[]=await api('torrents/info');if(!Array.isArray(before))throw Error('任务列表响应格式异常');
 let cursor='';if(native){try{const d=await api('diagnostics/add');if(d.status==='ready'&&typeof d.cursor==='string')cursor=d.cursor}catch{/* Diagnostic failure must not block or replay submission. */}}
 recent.current={before:before.map(x=>x.hash),cursor,at:Date.now()};setHasRecent(true);
 setStage('正在提交到 qB（请勿重复点击）…');sent=true;
 const response=await api('torrents/add',payload);if(typeof response==='string'&&response.trim()!=='Ok.'&&response.trim()!=='')throw Error('qB 未确认接受任务，请检查种子来源或文件');
 const pending=typeof response==='object'&&response!==null&&typeof response.pending_count==='number'?response.pending_count:0;
 setResult(`qB 已接受添加请求${pending>0?`，${pending} 项正在获取或解析`:''}；不代表成功，正在核验任务状态。`);setStage('正在观察实际任务与增量诊断（最长 45 秒）…');
 await observe();
 }catch(e){if(alive.current)setError(redact((e as Error).message)+(sent?'；请求可能已送达，请先检查任务列表，未自动重试。':''))}finally{sending.current=false;if(alive.current){setBusy(false);setStage('')}}}}>
 <div className="modal-head"><h2>添加任务</h2><button type="button" onClick={close}>关闭</button></div>
 <fieldset disabled={busy} style={{border:0,padding:0,margin:0}}><label>磁力链接或 BT 下载链接（HTTP/HTTPS）<textarea name="urls" rows={3} placeholder="magnet:?xt=urn:btih:… 或 https://可信来源/rss?id=…"/></label>
 <label>种子文件<input type="file" accept=".torrent" name="torrents" multiple/></label><label>保存位置<input name="savepath" value={savepath} onChange={e=>{edited.current=true;setSavepath(e.target.value)}} required/></label><DirectoryButton initialPath={()=>savepath} onConfirm={path=>{edited.current=true;setSavepath(path)}}/>
 <div className="form-grid"><label>分类（可选）<input name="category" placeholder="MoviePilot 分类"/></label><label>标签（可选，逗号分隔）<input name="tags" placeholder="电影, 4K"/></label></div>
 <label className="check"><input type="checkbox" name="stopped"/>添加后保持暂停</label></fieldset><p>默认请求开始下载，实际状态以 qB 返回为准。只添加有权下载的内容；不修改私有种子或网络发现设置。</p>
 {error&&<p role="alert" className="error danger-text">{error}</p>}{stage&&<p role="status">{stage}</p>}{result&&<p role="status">{result}</p>}{diagnostic&&<p>{diagnostic}</p>}{hasRecent&&<p>最近请求：{new Date(recent.current!.at).toLocaleTimeString()}；本页面关闭再打开保留结果，重新加载页面后清除。</p>}{hasRecent&&<button type="button" disabled={busy} onClick={()=>void refreshDiagnostics()}>刷新诊断</button>}<button className="primary" type="submit" disabled={busy}>{busy?'正在提交并观察…':'开始添加'}</button>
 </form></section></div>
}
