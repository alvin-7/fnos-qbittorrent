export const connectorReasons:Record<string,string>={
 connector_bind_failed:'监听失败：可能是端口已占用。检查专用 API 端口；旧配置保持不变，不要修改 BT 端口或自动重试',
 invalid_connector_scope_or_credentials:'配置参数无效：检查账号、密码和专用 API 端口',
 private_storage_permissions:'连接器私有存储权限不足：请由管理员检查应用私有数据目录；不要放宽为公共可写',
 connector_save_failed:'连接器配置未保存：检查应用私有存储的可写状态及可用空间；旧配置保持不变'
};
export function connectorFailure(reason:unknown){const code=typeof reason==='string'&&Object.hasOwn(connectorReasons,reason)?reason:'connector_save_failed';return `${connectorReasons[code]} [${code}]`}
type Input={enabled:boolean,port:string|number,username:string,password:string,passwordSet?:boolean};
export function connectorValidation(v:Input):string{
 const bytes=(s:string)=>new TextEncoder().encode(s).length;
 if(v.password&&(bytes(v.password)>1024||/[\u0000-\u001f\u007f]/.test(v.password)))return '专用密码必须为 1–1024 UTF-8 字节，不能包含控制字符；留空仅可保留已设置的密码';
 if(!v.enabled)return '';
 if(!v.username.trim()||bytes(v.username)>128||/[\r\n\0]/.test(v.username))return '专用账号不能为空，且须不超过 128 字节，不能包含换行或空字符';
 if(!v.password&&!v.passwordSet)return '启用前请设置非空专用密码（1–1024 UTF-8 字节）';
 const port=String(v.port);if(!/^\d+$/.test(port)||!Number.isInteger(Number(port))||Number(port)<1024||Number(port)>65535||[18080,49160].includes(Number(port)))return '专用 API 端口必须为 1024–65535 的整数，不能使用内部管理端口 18080 或默认 BT 端口 49160';
 return '';
}
