import './directory-picker.css';
import {createPortal} from 'react-dom';
import {usePageScrollLock} from './usePageScrollLock';
import {useEffect, useRef, useState} from 'react';
import {appBase, directoryMarker} from './api';

const messages: Record<string, string> = {
  AUTH_USER_ACL_DENIED: '当前用户的目录 ACL 未通过（AUTH_USER_ACL_DENIED）',
  AUTH_PACKAGE_READ_DENIED: '应用运行账号无目录读取权限（AUTH_PACKAGE_READ_DENIED）',
  AUTH_MOUNT_UNAVAILABLE: '授权目录不存在或挂载不可用（AUTH_MOUNT_UNAVAILABLE）',
  AUTH_MOUNT_REJECTED: '目录挂载身份变化或路径链接被安全拒绝（AUTH_MOUNT_REJECTED）',
  AUTH_PRIVATE_ROOTS_EXCLUDED: '授权仅包含应用私有目录，已安全排除（AUTH_PRIVATE_ROOTS_EXCLUDED）',
  AUTH_TOKEN_MISSING: '启动环境缺少平台授权认证（AUTH_TOKEN_MISSING）',
  AUTH_ROOTS_INACCESSIBLE: '应用有授权记录，但当前用户权限或挂载不可访问（AUTH_ROOTS_INACCESSIBLE）',
  AUTH_TOKEN_REJECTED: '平台授权认证不可用（AUTH_TOKEN_REJECTED）',
  AUTH_SCOPE_DENIED: '应用查询授权权限不足（AUTH_SCOPE_DENIED）',
  AUTH_API_UNAVAILABLE: '系统不提供授权查询接口（AUTH_API_UNAVAILABLE）',
  AUTH_REQUEST_INVALID: '授权查询参数不符合平台合同（AUTH_REQUEST_INVALID）',
  AUTH_RESPONSE_INVALID: '平台授权响应无法解析（AUTH_RESPONSE_INVALID）',
  AUTH_SOURCE_UNAVAILABLE: '当前平台无法核实本应用授权目录，请检查系统版本和应用授权后重试',
  DIRECTORY_UNAVAILABLE: '目录不可用或未授权', AUTHORIZATION_CHANGED: '授权已变化，请重新加载',
  CURSOR_EXPIRED: '目录分页已过期，请重新加载', READ_ONLY: '此目录只读，不能用于下载',
  BROWSE_TIMEOUT: '读取超时，请重试',
};

export async function directoryRequest(action: string, data: object = {}, signal?: AbortSignal) {
  const r = await fetch(`${appBase()}/gateway/directories/${action}`, {
    method: 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: {'Content-Type': 'application/json', 'X-Fnos-CSRF': await directoryMarker()},
    body: JSON.stringify(data), signal: signal ?? AbortSignal.timeout(6000),
  });
  let d: any;
  try { d = await r.json(); } catch { throw Error('目录服务不可用，请重试'); }
  if (!r.ok) throw Error(messages[d.code] || '目录服务不可用，请重试');
  return d;
}

type Entry = {rootId: string; name: string; relativePath: string; canonicalPath: string; writable: boolean};
type Layer = {entries: Entry[]; nextCursor: string; reason?: string; diagnostics?: {stage?: string; counts?: Record<string, number>}};
function layerStatus(layer?: Layer) {
  if (!layer) return '尚未读取此目录，请重试';
  const title = layer.reason === 'DIRECTORY_EMPTY' ? '目录读取返回空列表' : layer.reason === 'DIRECTORY_CHILDREN_FILTERED' || layer.reason === 'DIRECTORY_PAGE_FILTERED' ? '子目录已被安全过滤' : '此目录未返回可显示的子目录';
  const labels: Record<string, string> = {scanned: '扫描到', directories: '目录候选', returned: '返回', ACL_API_DENIED: '用户ACL接口拒绝（ACL_API_DENIED）', PACKAGE_OPEN_EACCES: '包账号打开拒绝（PACKAGE_OPEN_EACCES）', MOUNT_REJECTED: '根挂载身份拒绝（MOUNT_REJECTED）', SYMLINK_REJECTED: '符号链接拒绝（SYMLINK_REJECTED）', child_open_rejected: 'child_open拒绝', childRejected: 'child_check拒绝', non_directory: '非目录', mount_unavailable: '挂载不可用', unavailable: '文件系统错误'};
  const counts = Object.entries(labels).flatMap(([key, label]) => { const value = layer.diagnostics?.counts?.[key]; return Number.isSafeInteger(value) && value! >= 0 ? [`${label} ${value}`] : []; });
  return `${title} · browse_children${counts.length ? ' · ' + counts.join('，') : ''}`;
}
const folder = <svg className="directory-folder" viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 7V5a1 1 0 0 1 1-1h6l2 3h8a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V7Z"/><path d="M3 8h18"/></svg>;

export function DownloadDirectoryPicker({initialPath, onConfirm, onCancel}: {initialPath: string; onConfirm: (path: string) => void; onCancel: () => void}) {
  usePageScrollLock();
  const [roots, setRoots] = useState<Entry[]>([]), [revision, setRevision] = useState('');
  const [choice, setChoice] = useState<Entry>(), [layers, setLayers] = useState<Record<string, Layer>>({});
  const [expanded, setExpanded] = useState<Record<string, boolean>>({}), [error, setError] = useState('');
  const [busy, setBusy] = useState(false), [pathOpen, setPathOpen] = useState(false);
  const generation = useRef(0), controller = useRef<AbortController | undefined>(undefined), dialog = useRef<HTMLElement>(null);
  const origin = useRef(document.activeElement as HTMLElement | null);
  const key = (e: Entry) => `${e.rootId}:${e.relativePath}`;
  const root = roots.find(e => e.rootId === choice?.rootId);
  const selectedKey = choice ? key(choice) : '';

  useEffect(() => { const before = origin.current; void loadRoots(); dialog.current?.focus(); return () => { generation.current++; controller.current?.abort(); before?.focus(); }; }, []);
  async function request(fn: (signal: AbortSignal, generation: number) => Promise<void>, destructive = false) {
    controller.current?.abort(); const c = new AbortController(); controller.current = c; const g = ++generation.current;
    setBusy(true); setError('');
    try { await fn(AbortSignal.any([c.signal, AbortSignal.timeout(6000)]), g); }
    catch (e) { if (g === generation.current && (e as Error).name !== 'AbortError') { setError((e as Error).name === 'TimeoutError' ? messages.BROWSE_TIMEOUT : (e as Error).message); if (destructive || (e as Error).message === messages.AUTHORIZATION_CHANGED) { setRoots([]); setChoice(undefined); setLayers({}); setExpanded({}); } } }
    finally { if (g === generation.current) setBusy(false); }
  }
  async function loadRoots() {
    setChoice(undefined); setLayers({}); setExpanded({});
    await request(async (signal, g) => { const d = await directoryRequest('roots', {}, signal); if (g !== generation.current) return;
      setRoots(d.roots || []); setRevision(d.authorizationRevision || '');
      if (initialPath) { try { const c = await directoryRequest('validate', {manualPath: initialPath}, signal); if (g === generation.current) setChoice({...c, name: c.canonicalPath.split('/').at(-1) || c.canonicalPath}); } catch { /* historical parent value is not a candidate */ } }
    }, true);
  }
  async function browse(e: Entry, append = false) {
    const old = layers[key(e)];
    await request(async (signal, g) => { const d = await directoryRequest('browse', {rootId: e.rootId, relativePath: e.relativePath, authorizationRevision: revision, cursor: append ? old?.nextCursor : undefined}, signal); if (g !== generation.current) return;
      const entries: Entry[] = append ? [...(old?.entries || []), ...(d.entries || [])] : (d.entries || []);
      setLayers(x => ({...x, [key(e)]: {entries: [...new Map(entries.map((v: Entry) => [key(v), v])).values()] as Entry[], nextCursor: d.nextCursor || '', reason: d.reason, diagnostics: d.diagnostics}}));
      setExpanded(x => ({...x, [key(e)]: true}));
    });
  }
  function select(e?: Entry) {
    // Navigation owns the candidate; older browse/validate results cannot restore it.
    generation.current++; controller.current?.abort(); setBusy(false);
    setChoice(e); setError('');
  }
  function navigate(e?: Entry) { select(e); if (e) void browse(e); }
  const breadcrumb = choice?.relativePath.split('/').filter(Boolean) || [];
  function renderTree(e: Entry, depth = 0): React.ReactNode {
    const k = key(e), selected = selectedKey === k, open = !!expanded[k], layer = layers[k];
    return <div className="directory-node" key={k}><div className={`directory-row${selected ? ' selected' : ''}`} role="treeitem" aria-level={depth + 1} aria-selected={selected} aria-expanded={open}>
      <button className="directory-toggle" type="button" disabled={!layer && false} aria-label={`${open ? '收起' : '展开'} ${e.name}`} onClick={() => open ? setExpanded(x => ({...x, [k]: false})) : void browse(e)}>{open ? '⌄' : '›'}</button>
      <button className="directory-pick" type="button" title={e.canonicalPath} onClick={() => select(e)}>{folder}<bdi>{e.name}</bdi>{selected && <span className="directory-tick" aria-label="已选中">✓</span>}</button>
    </div>{open && <div className="directory-branch" role="group">{layer?.entries.map(child => renderTree(child, depth + 1))}{layer?.nextCursor && <button className="directory-more" type="button" disabled={busy} onClick={() => void browse(e, true)}>继续读取</button>}{!busy && layer && !layer.entries.length && !layer.nextCursor && <p className="directory-state">{layerStatus(layer)}</p>}</div>}</div>;
  }
  const mobileEntries = choice ? layers[selectedKey]?.entries || [] : roots;
  return createPortal(<div className="overlay directory-overlay" onClick={e => { if (e.target === e.currentTarget) onCancel(); }}><section className="directory-picker" ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="directory-picker-title" onKeyDown={e => {
    if (e.key === 'Escape') { e.stopPropagation(); onCancel(); }
    if (e.key === 'Tab') { const items = [...dialog.current!.querySelectorAll<HTMLElement>('button:not(:disabled)')].filter(x => x.getClientRects().length); const first = items[0], last = items.at(-1); if (first && last && ((e.shiftKey && document.activeElement === first) || (!e.shiftKey && document.activeElement === last))) { e.preventDefault(); (e.shiftKey ? last : first).focus(); } }
  }}>
    <header><div><h2 id="directory-picker-title">选择下载目录</h2><p>仅显示飞牛授予本应用访问权限的目录</p></div><button className="directory-close" type="button" aria-label="关闭目录选择器" onClick={onCancel}>×</button></header>
    <nav className="directory-crumbs" aria-label="目录面包屑"><button type="button" onClick={() => navigate()}>已授权目录</button>{root && <><span aria-hidden="true">›</span><button type="button" onClick={() => navigate(root)}>{root.name}</button></>}{breadcrumb.map((name, i) => <span key={`${name}-${i}`}><span aria-hidden="true">›</span><button type="button" onClick={() => root && navigate({...root, relativePath: breadcrumb.slice(0, i + 1).join('/'), canonicalPath: `${root.canonicalPath}/${breadcrumb.slice(0, i + 1).join('/')}`, name})}>{name}</button></span>)}</nav>
    <div className="directory-scope"><span>{choice ? '当前目录 · 按需读取' : '授权范围内 · 按需浏览'}</span><button type="button" disabled={busy} onClick={() => void loadRoots()}>刷新授权状态</button></div>
    <div className="directory-content" aria-busy={busy}>{busy && <p className="directory-state" role="status">正在读取授权目录…</p>}{error && <p className="directory-state error" role="alert">{error}<button type="button" onClick={() => void (choice ? browse(choice) : loadRoots())}>重试</button></p>}{!busy && !error && !roots.length && <p className="directory-state" role="status">没有已授权目录，请在应用设置授权后刷新。</p>}
      <div className="directory-tree" role="tree" aria-label="已授权目录树">{!error && roots.map(e => renderTree(e))}</div>
      <div className="directory-mobile-list">{!error && mobileEntries.map(e => <button className={`directory-mobile-row${selectedKey === key(e) ? ' selected' : ''}`} type="button" key={key(e)} title={e.canonicalPath} onClick={() => navigate(e)}>{folder}<bdi>{e.name}</bdi><span aria-hidden="true">›</span></button>)}{choice && !busy && !layers[selectedKey]?.entries.length && <p className="directory-state" role="status">{layerStatus(layers[selectedKey])}</p>}</div>
    </div>
    <footer><small>当前完整路径</small><div className={`directory-path${pathOpen ? ' expanded' : ''}`}><bdi title={choice?.canonicalPath}>{choice?.canonicalPath || '尚未选择目录'}</bdi><button type="button" onClick={() => setPathOpen(x => !x)} aria-expanded={pathOpen}>{pathOpen ? '收起' : '展开'}</button></div><div role="status" className={`directory-permission${choice && !choice.writable ? ' warning' : ''}`}>{choice && !choice.writable ? messages.READ_ONLY : choice ? '可用于下载，确认时将重新验证' : '请选择授权目录'}</div><div className="directory-actions"><button type="button" onClick={onCancel}>取消</button><button className="primary" type="button" disabled={busy || !choice?.writable || !!error} onClick={() => void request(async (signal, g) => { const c = await directoryRequest('validate', {rootId: choice!.rootId, relativePath: choice!.relativePath, authorizationRevision: revision}, signal); if (g === generation.current) onConfirm(c.canonicalPath); })}>使用此目录</button></div></footer>
  </section></div>, document.body);
}

export function DirectoryButton({initialPath, onConfirm}: {initialPath: () => string; onConfirm: (path: string) => void}) { const [open, setOpen] = useState(false); if ((import.meta as any).env.VITE_NATIVE !== '1') return null; return <><button type="button" className="directory-trigger" onClick={() => setOpen(true)}>选择目录</button>{open && <DownloadDirectoryPicker initialPath={initialPath()} onCancel={() => setOpen(false)} onConfirm={path => { onConfirm(path); setOpen(false); }}/>}</>; }
