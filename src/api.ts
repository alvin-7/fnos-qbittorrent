import {connectorFailure} from './connectorValidation';
// Gateway credentials live in memory only: never URL/localStorage/log output.
export function appBase(pathname=window.location.pathname){const p='/app/fnos-qbittorrent';return pathname===p||pathname.startsWith(p+'/')?p:''}
export function apiPath(path:string){return `${appBase()}/api/v2/${path}`}
const reasons:Record<string,string>={missing_trim_identity:'fnOS 未提供管理员身份',origin_or_referer_missing:'请求缺少来源信息',origin_referer_mismatch:'Origin 与 Referer 不一致或格式无效',fetch_site_not_same_origin:'请求不是同源 Fetch',session_cookie_missing:'未收到应用会话 Cookie',session_expired:'应用会话已过期或不存在',session_origin_mismatch:'应用会话来源不匹配',session_uid_mismatch:'应用会话用户不匹配',csrf_missing_or_invalid:'CSRF 令牌缺失或无效',backend_403:'qB 后端拒绝访问',native_policy_forbidden:'原生安全策略禁止此操作'};
async function forbidden(r:Response){const reason=r.headers.get('X-Fnos-Gateway-Reason')||'';let suffix='';if(reason==='session_origin_mismatch'){try{const d=await r.clone().json();suffix=`；双方指纹 ${d.session_origin_fingerprint}/${d.request_origin_fingerprint}，端口类别 ${d.session_origin_port_class}/${d.request_origin_port_class}；bootstrap_origin_changed=${d.bootstrap_origin_changed}`}catch{}}const code=Object.hasOwn(reasons,reason)?reason:'unclassified_403';return new Error((reasons[code]||'访问被拒绝，原因未分类')+' ['+code+']'+suffix+'；不自动重发业务操作')}
let token='';let bootstrap:Promise<string>|undefined;
async function gatewayToken(){
 if(token)return token;
 if(!bootstrap)bootstrap=(async()=>{
  const r=await fetch(`${appBase()}/gateway/session`,{method:'POST',credentials:'same-origin',referrerPolicy:'same-origin',cache:'no-store',headers:{'X-Fnos-Bootstrap':'1'},signal:AbortSignal.timeout(20000)});
  if(!r.ok)throw Object.assign(r.status===403?await forbidden(r):new Error('fnOS 网关会话不可用 [bootstrap_unavailable]；请保留此代码定位，不自动重发业务操作'),{code:r.status,stage:'bootstrap',reason:r.status===403?'gateway_rejected':'bootstrap_unavailable'});
  const data=await r.json();if(typeof data.token!=='string'||!data.token)throw Object.assign(Error('网关没有返回安全令牌 [bootstrap_invalid_response]；请保留此代码定位，不自动重发业务操作'),{stage:'bootstrap',reason:'bootstrap_invalid_response'});token=data.token;return token;
 })().finally(()=>{bootstrap=undefined});
 return bootstrap;
}
export async function api(path:string,body?:URLSearchParams|FormData){
 const gateway=!!appBase();
 const method=body?'POST':'GET';
 const request=async()=>{const headers:Record<string,string>={};if(gateway)headers['X-Fnos-CSRF']=(import.meta as any).env.VITE_NATIVE==='1'?'gateway-request-v1':await gatewayToken();try{return await fetch(apiPath(path),{credentials:'same-origin',referrerPolicy:'same-origin',cache:'no-store',method,body,headers,signal:AbortSignal.timeout(20000)})}catch{throw new Error('连接失败或等待响应超时（20 秒）；无法确认服务端处理结果，请检查任务列表后再决定是否重试')}};
 let r=await request();
 // A session rejection clears only in-memory state. Rebuild once for safe reads;
 // never replay a business POST/DELETE after the server has seen it.
 if(gateway&&r.status===403&&r.headers.get('X-Fnos-Gateway-Error')==='session'){
  token='';
  if(method==='GET')r=await request();
 }
 if(!r.ok){if(path==='connector/configure'&&r.status===409){let reason:unknown;try{reason=(await r.json()).reason}catch{}throw Object.assign(new Error(connectorFailure(reason)),{code:409,stage:'connector_configure'})}if(r.status===401)throw Object.assign(new Error('qB 拒绝请求（401，Host/CSRF 校验）'),{code:401});if(r.status===403)throw Object.assign(gateway?await forbidden(r):new Error('需要登录 qBittorrent（403）'),{code:403});throw new Error(`请求失败 (${r.status})`)}
 if(gateway&&path==='auth/logout')token='';
 const text=await r.text();try{return JSON.parse(text)}catch{return text}
}
