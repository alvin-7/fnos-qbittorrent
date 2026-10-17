import {useEffect,useState} from 'react';
import {api} from './main';
import {bytes,stateName,redact} from './TorrentList';import {runTorrentAction} from './pt';
const value=(n:unknown)=>n===undefined||n===null||typeof n==='number'&&n<0?'—':String(n);
const size=(n:number)=>Number.isFinite(n)&&n>=0?bytes(n):'—';
const limit=(n:number)=>n===undefined?'—':n<=0?'不限速':bytes(n)+'/s';
// qB release-5.2.4 TrackerEndpointState; 0 is only pseudo-tracker disabled.
const trackerState=(n:number)=>({0:'已禁用',1:'未联系',2:'工作正常',4:'未工作',5:'Tracker 返回错误',6:'无法连接'} as Record<number,string>)[n]||'未知状态';
export function Detail({hash,close}:{hash:string,close:()=>void}){
 const [busy,setBusy]=useState(false),[notice,setNotice]=useState('');const [p,setP]=useState<any>(),[t,setT]=useState<any>(),[files,setFiles]=useState<any[]>([]),[trackers,setTrackers]=useState<any[]>([]),[global,setGlobal]=useState<any>(),[error,setError]=useState(''),[warnings,setWarnings]=useState<string[]>([]);
 useEffect(()=>{let active=true;const load=async()=>{
 const paths=['torrents/properties?hash='+hash,'torrents/info?hashes='+hash,'torrents/files?hash='+hash,'torrents/trackers?hash='+hash,'transfer/info'];
 const results=await Promise.allSettled(paths.map(path=>api(path)));if(!active)return;
 const failures:string[]=[];results.forEach((r,i)=>{if(r.status==='rejected'){failures.push(['属性','任务状态','文件','Tracker','全局连接'][i]+'读取失败：'+redact(r.reason?.message));return}const v=r.value;if(i===0)setP(v);if(i===1)setT(v[0]||null);if(i===2)setFiles(v);if(i===3)setTrackers(v);if(i===4)setGlobal(v)});setWarnings(failures);
 };void load();const id=setInterval(load,3000);return()=>{active=false;clearInterval(id)}},[hash]);
 const metric=(label:string,v:unknown)=><p className="wrap">{label}：{value(v)}</p>;
 const metadata=p?.has_metadata===true?'已获取':p?.has_metadata===false||/metaDL/i.test(t?.state||'')?'等待获取（API 未提供百分比）':'未知';
 const currentRatio=Number(p?.share_ratio??t?.ratio);const ratioLimit=Number(p?.max_ratio??t?.max_ratio);const ratioEnabled=Number.isFinite(ratioLimit)&&ratioLimit>0;const ratioPolicyPaused=ratioEnabled&&currentRatio>=ratioLimit&&/^(stopped|paused)/.test(t?.state||'');
 return <div className="overlay" onClick={e=>{if(e.target===e.currentTarget)close()}}><section role="dialog" aria-modal="true" aria-label="任务详情" aria-busy={busy} className="modal persistent-close"><div className="modal-head"><h2>任务详情</h2><button aria-label="关闭任务详情" onClick={close}>关闭</button></div>
 {error&&<p role="alert" className="error">{redact(error)}</p>}{warnings.map(w=><p role="alert" className="error" key={w}>{w}（保留上次数据，可能已过时）</p>)}
 {!p&&!t?<p>加载详情…</p>:<>
 <h3 className="wrap">{redact(t?.name||'任务')}</h3>{metric('真实状态',t?`${stateName(t)} (${t.state})`:'暂不可得')}
 {t&&/error|missingFiles/i.test(t.state)&&<p role="alert" className="error">qB 报告磁盘/文件异常。检查保存路径、空间和权限；WebAPI 未提供具体磁盘错误文本，请查看 qB 日志。</p>}
 {t?.error&&metric('任务错误',redact(t.error))}{metric('元数据',metadata)}{metric('内容进度',t?.progress===undefined?'—':(t.progress*100).toFixed(1)+'%')}{metric('分享率策略',ratioEnabled?`当前 ${Number.isFinite(currentRatio)?currentRatio:'—'}；阈值 ${ratioLimit}（上传 / 下载）；${ratioPolicyPaused?'已因策略暂停':'未因策略暂停'}`:'关闭')}
 {notice&&<p role="status">{notice}</p>}{t&&<><div className="modal-actions">{(['start','force','stop'] as const).map((action,i)=><button key={action} disabled={busy} onClick={async()=>{if(busy)return;setBusy(true);setError('');setNotice('操作中…');try{const actual=await runTorrentAction(api,action,hash);setT(actual);setNotice('已回读状态：'+actual.state+'；force='+actual.force_start)}catch(e){setError((e as Error).message);setNotice('未确认；未自动重发')}finally{setBusy(false)}}}>{['开始','强制开始','暂停'][i]}</button>)}</div><p>已完成任务开始 = 继续做种。强制开始越过队列；不承诺忽略分享率、做种时长或限速。操作后回读真实状态，失败不自动重发。</p></>}
 {metric('做种时间（秒）',p?.seeding_time??t?.seeding_time)}
 <div className="stats"><div>下载速度<strong>{size(t?.dlspeed??p?.dl_speed)}/s</strong></div><div>上传速度<strong>{size(t?.upspeed??p?.up_speed)}/s</strong></div><div>总大小<strong>{size(p?.total_size??t?.size)}</strong></div><div>分享率<strong>{value(p?.share_ratio??t?.ratio)}</strong></div></div>
 {metric('连接种子 / 总种子',`${value(t?.num_seeds??p?.seeds)} / ${value(t?.num_complete??p?.seeds_total)}`)}
 {metric('连接 Peer / 总 Peer',`${value(t?.num_leechs??p?.peers)} / ${value(t?.num_incomplete??p?.peers_total)}`)}
 {metric('连接数 / 上限',`${value(p?.nb_connections)} / ${value(p?.nb_connections_limit)}`)}{metric('可用性',t?.availability)}
 <p>PT 优先：DHT、PeX、LSD 保持关闭，UPnP 默认关闭；不通过开启发现功能解决零速度。请检查 Tracker 认证、种子连接及入站监听；私有标记仅展示，不修改。</p><p>0 速度本身不能证明网络故障。请结合元数据、种子连接、Tracker、排队和磁盘状态判断；本界面没有进行网络测速。</p>
 <details><summary>Tracker 诊断</summary>{trackers.some(tr=>/^https?:|^udp:/i.test(tr.url)&&/port\s+\d+\s+is\s+blacklisted/i.test(tr.msg||''))&&<p role="alert" className="error">Tracker 拒绝 BT 端口：请关闭详情，打开 设置 → BT 监听端口，按站点规则改为固定高位端口（建议 49160）并保存。不会自动改现有端口或路由映射；保存不代表 Tracker 已接受，请等待下次汇报后检查消息。</p>}{['实际 Tracker','发现机制（私有种子禁用属正常）'].map((group,j)=><div key={group}><h4>{group}</h4>{trackers.filter(tr=>j?!/^(https?|udp):/i.test(tr.url):/^(https?|udp):/i.test(tr.url)).map((tr,i)=><div key={i}><p className="wrap">{redact(tr.url)} · {trackerState(tr.status)} ({tr.status}){tr.is_updating?' · 更新中':''}</p><p className="wrap">消息：{redact(tr.msg||'无')} · 种子 {value(tr.num_seeds)} / Peer {value(tr.num_leeches)}</p></div>)}</div>)}{!trackers.length&&<p>未返回 Tracker 数据</p>}<small>URL 路径及查询参数已脱敏；不提供敏感链接跳转。</small></details>
 <details><summary>高级任务信息</summary>
 {metric('Hash',hash)}{metric('保存位置',redact(p?.save_path??t?.save_path))}{metric('临时下载位置',redact(p?.download_path??t?.download_path))}
 {metric('ETA',t?.eta>=0&&t?.eta<8640000?Math.ceil(t.eta/60)+' 分钟':'未知')}{metric('队列优先级',t?.priority)}
 {metric('下载限速',limit(p?.dl_limit??t?.dl_limit))}{metric('上传限速',limit(p?.up_limit??t?.up_limit))}
 {metric('本会话下载 / 上传',`${size(p?.total_downloaded_session)} / ${size(p?.total_uploaded_session)}`)}{metric('累计下载 / 上传',`${size(p?.total_downloaded??t?.downloaded)} / ${size(p?.total_uploaded??t?.uploaded)}`)}{metric('已完成内容量',size(t?.completed))}
 {metric('私有种子',p?.private===true?'是（遵守站点规则）':p?.private===false?'否':'未知')}
 {metric('全局 DHT 节点',global?.dht_nodes)}{metric('全局连接状态',global?.connection_status)}<p>全局连接状态不等于端口外网可达测试；transfer/info 不提供监听端口的可达性证明。</p>
 {metric('全局下载 / 上传限速',`${limit(global?.dl_rate_limit)} / ${limit(global?.up_rate_limit)}`)}
 <button onClick={async()=>{try{await api('torrents/recheck',new URLSearchParams({hashes:hash}))}catch(e){setError((e as Error).message)}}}>重新校验</button></details>
 <h3>文件列表</h3><ul className="files">{files.map(f=><li key={f.index}><span className="wrap">{redact(f.name)}</span><small>{size(f.size)} · {(f.progress*100).toFixed(1)}%</small><progress max={1} value={f.progress}/></li>)}</ul>
 </>}</section></div>
}
