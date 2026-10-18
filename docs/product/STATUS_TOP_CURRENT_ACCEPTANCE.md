# 当前源码顶部状态与取消筛选回归

## 结果

- `node tools/verify_status_filters.mjs`：PASS。state 语义、null / [] 站点区别、组合条件移除、单套导航契约。
- 新功能 RED：修改前同一测试 `seeding` 返回 0，期望 4，确实失败后实现。
- `node tools/verify_status_refresh_race.mjs`：历史 `git show HEAD:src/main.tsx` 的真实 refresh 在较新任务快照后收到旧空快照，最终 0；当前函数最终 1。通过内存 VM + TypeScript 转译执行，未覆盖未提交源码。
- `python tools/verify_status_current.py`：PASS 当前源码原生前缀 Vite 产物 + 当前 gateway Go test server 的真实 Unix socket + 本地隔离 qBittorrent v5.2.4。1440×844、390×844 iframe 真实 Chromium 点击通过，非模拟 API 列表。
- `npm run build`：最终 PASS。早期碰到并行 picker 未完成时的 TS 错误，未修改 picker，待其实现者完成后已通过。

## 浏览器覆盖

顶部五项逐一点击，aria-pressed、计算色值白字/深蓝、44px；手机局部横滑、桌面正常一行；侧栏和抽屉无重复；搜索最后条件移除；分类/标签摘要移除；分析站点返回与移除；组合搜索/分类/状态统一清除；全部仅清状态；筛选变化清选择；分析无状态条；无 JS error；业务 POST 为 0。

较旧空列表延迟 6800ms、后续轮询保留真实 qB 完整快照；旧空响应落地后仍显示 2 项。此 race 单点是测试注入，不称真实网络恰好发生。

API POST 中分析页 `/gateway/directories/storage` 是只读容量查询，单独排除于业务写计数；测试没有发送 torrents/preferences 等业务写。fixture 创建分类/标签/任务仅由隔离后端 harness 完成，不是 UI 筛选副作用。

证据：`evidence/status-current-browser.json`、`evidence/status-current-1440.png`、`evidence/status-current-390.png`。本轮运行目录 `.runtime/status-current-4906dd98/`。

## 边界

- 未打包、未改目录 picker/backend、未提交/推送、未访问 NAS。测试 gateway 使用现有 test server/provider，真实 Unix 传输，但平台权限来源是测试模拟，不是 NAS ACL。
- “手动取消后无任务”已证明旧 refresh 确有可复现竞态、当前可防护，且最终条件移除真实浏览器恢复。不能据此断言用户现场唯一根因。
- 新目录 picker 的展开/分层/面包屑/内滚/背景锁/仅回填完整浏览器回归未合并入本轮；父代理应统一集成测试，不能把本轮状态测试算作 picker 验收。
