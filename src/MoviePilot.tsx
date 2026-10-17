import {useEffect,useState,useRef} from 'react';import {api} from './api';import {connectorValidation} from './connectorValidation';
type Config={enabled:boolean,port:number|string,username:string,passwordSet?:boolean,listening?:boolean};
export function MoviePilot(){
 const [cfg,setCfg]=useState<Config>({enabled:false,port:18081,username:'moviepilot'}),[password,setPassword]=useState(''),[shownPassword,setShownPassword]=useState(''),[showPassword,setShowPassword]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[result,setResult]=useState('');
 const revealTimer=useRef<ReturnType<typeof setTimeout>|undefined>(undefined),revealEpoch=useRef(0);
 function clearReveal(){revealEpoch.current++;if(revealTimer.current!==undefined)clearTimeout(revealTimer.current);revealTimer.current=undefined;setShownPassword('');setShowPassword(false)}
 useEffect(()=>()=>{revealEpoch.current++;if(revealTimer.current!==undefined)clearTimeout(revealTimer.current)},[]);
 async function load(){const x=await api('connector/status');setCfg(x);clearReveal()}
 useEffect(()=>{void load().catch(e=>setError(e.message))},[]);
 async function act(fn:()=>Promise<void>){setBusy(true);setError('');try{await fn()}catch(e){setError((e as Error).message+'；未自动重试')}finally{setBusy(false)}}
 return <section aria-label="MoviePilot 连接器" aria-busy={busy} className="settings-group"><h3>MoviePilot 连接器</h3><p>同 NAS Docker → host.docker.internal。独立账号，不使用内部 qB 管理员密码。认证后可调用完整 qB 业务 API（含删除任务/文件、修改偏好）；专用高熵密码与NAS防火墙是安全边界。HTTP 明文传输账号密码与业务数据。安全依赖NAS防火墙，不适合公网。默认监听 0.0.0.0（所有 NAS IPv4 接口）。</p><p role="status">配置：{cfg.enabled?'已启用':'关闭'}；监听：{cfg.listening?'运行中':'未运行'}；容器可达：未验收（本机测试不代表容器成功）</p>
 <label className="check"><input type="checkbox" checked={cfg.enabled} onChange={e=>setCfg({...cfg,enabled:e.target.checked})}/>启用 MoviePilot 连接器</label>
 <label>专用 API 端口<input inputMode="numeric" value={cfg.port} onChange={e=>setCfg({...cfg,port:e.target.value})}/></label>
 <label>专用账号<input autoComplete="off" value={cfg.username||''} onChange={e=>setCfg({...cfg,username:e.target.value})}/></label>
 <label>专用密码{cfg.passwordSet?'（已设置；留空保留）':'（UTF-8 不超过 1024 字节）'}<span className="password-field"><input type={showPassword?'text':'password'} autoComplete="new-password" value={showPassword&&shownPassword?shownPassword:password} onChange={e=>{setPassword(e.target.value);setShownPassword('')}} aria-label="MoviePilot 专用密码（新密码，不回填已保存密码）"/><button type="button" className="password-toggle" aria-label={showPassword?'隐藏 MoviePilot 专用密码':'显示 MoviePilot 专用密码'} aria-pressed={showPassword} onPointerDown={e=>e.preventDefault()} onClick={()=>{if(showPassword){clearReveal();return}void act(async()=>{if(!cfg.passwordSet){setShowPassword(v=>!v);return}if(!confirm('管理员二次确认：临时显示已保存密码？'))return;const epoch=++revealEpoch.current;const r=await api('connector/password/reveal',new URLSearchParams({confirm:'show-saved-password'}));if(epoch!==revealEpoch.current)return;setShownPassword(String(r.password||''));setShowPassword(true);revealTimer.current=setTimeout(clearReveal,30000)})}} style={{WebkitTapHighlightColor:"transparent"}}>{showPassword?'隐藏':'显示'}</button></span></label>
 <p>客户端地址：http://host.docker.internal:{cfg.port}。分类路径不等于 MoviePilot 容器路径映射；挂载、权限、文件可达须另行验收。</p>
 <button type="button" disabled={busy} onClick={()=>{const invalid=connectorValidation({...cfg,password});setResult('');if(invalid){setError(invalid);return}if(!confirm(`保存${cfg.enabled?'并启用':'并禁用'}连接器？监听所有 NAS IPv4 接口 0.0.0.0:${cfg.port}；安全依赖NAS防火墙，不适合公网。所有旧会话立即撤销；HTTP 为明文。`))return;void act(async()=>{await api('connector/configure',new URLSearchParams({json:JSON.stringify({enabled:cfg.enabled,port:Number(cfg.port),username:cfg.username,password})}));setPassword('');await load();setResult('配置已保存并读回；容器可达性尚未验收')})}}>保存连接器配置</button>
 <button type="button" disabled={busy} onClick={()=>void act(async()=>{const r=await api('connector/test',new URLSearchParams());setResult(r.backendReady?'后端只读探针：qB 5.2.4 就绪；容器可达仍未验收':'后端未就绪；容器可达未验收')})}>只读测试后端</button>
 {error&&<p role="alert" className="error" ref={el=>el?.scrollIntoView({block:'center'})}>{error}</p>}{result&&<p role="status">{result}</p>}
 </section>
}
