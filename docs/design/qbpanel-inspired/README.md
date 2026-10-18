# OpenDesign 评审记录：手机添加入口（2026-10-18）

## 评审决定
- 手机 Dock 仅保留「筛选」「设置」；添加任务改为独立右下 FAB。FAB 使用加号与清晰 `aria-label=添加任务`，在手机显示「添加」文字。桌面侧栏与桌面 Dock 的主添加入口保持不变。
- FAB 与 Dock 使用 safe-area 底部间距；任务区增加底部 padding，确保末项及任务动作完整滚出浮层上方。选择模式互斥隐藏普通 Dock 与 FAB，仅显示批量栏。添加弹层、设置、筛选打开期间隐藏 FAB，避免遮挡与穿透误点；弹层锁定背景并保留表单。
- 设计验证尺寸为 360×780、390×844 与 1440×1024；软键盘以弹层内部滚动、固定头尾和背景锁定模拟。

## OpenDesign artifact 真实读回
- 真实项目：`fnos-pt-workspace-redesign`。
- `sync.py` 已将 `workspace.html` 注册为 `desktop.html` / `mobile.html`，并逐文件 GET 精确读回后才导出。
- OpenDesign PNG 是 daemon 原生 `export/image` 输出；`*-viewport.png` 是从精确读回 artifact 在 Chromium viewport 截取的浏览器预览，二者有意区分。

## 预览与验证
- 手机原型：`docs/design/qbpanel-inspired/mobile.html`
- 桌面原型：`docs/design/qbpanel-inspired/desktop.html`
- 原生 OpenDesign 导出：`mobile.png`、`desktop.png`
- 浏览器 viewport 导出：`mobile-viewport.png`、`narrow-viewport.png`、`desktop-viewport.png`
- 真实读回与导出：`python3 docs/design/qbpanel-inspired/sync.py`
- 交互回归：`node docs/design/qbpanel-inspired/verify.cjs` → **45 passed / 3 devices**（desktop、390、360），无 JS 错误、无外部业务请求。覆盖 FAB 添加/取消、筛选保留、选择互斥、弹层锁定、末项滚出、44px 触控与桌面不回归。

本目录仅为 OpenDesign 原型与验证证据，不修改产品 `src`，不连接 NAS，不执行下载，不提交 Git。
