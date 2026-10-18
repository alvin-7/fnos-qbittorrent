# fnOS PT 下载目录选择器 · OpenDesign 实际交付

## 真实工具与项目

- 已发现 Windows 安装并运行的 **Open Design 0.25.0**：`%USERPROFILE%\AppData\Local\Programs\Open Design\Open Design.exe`。
- 本次实际调用其本机 daemon HTTP API：`http://127.0.0.1:10012`；Web UI：`http://127.0.0.1:10010`。端口可能随应用重启变化。
- 独立项目 ID：`fnos-pt-download-directory-picker`。
- 项目名称：`fnOS PT · 下载目录选择器 · 设计评审`。
- Conversation ID：`abfee486-c5f7-4de0-95f1-ec107b0c150b`。
- 项目实际路径：`%USERPROFILE%\AppData\Roaming\Open Design\namespaces\release-stable-win\data\projects\fnos-pt-download-directory-picker`。
- 用 `POST /api/projects` 创建项目并 GET 原目标读回；用 `POST /api/projects/{id}/files` 创建两个 artifact，OpenDesign 真实生成 ArtifactManifest、HTML 版本记录；读回文件核对；用其 `POST /api/projects/{id}/export/image` **实际渲染导出 PNG**。不是将外部 HTML 口头冒充为 OpenDesign 项目，也未声称由 OpenDesign 内置 AI 生成。

## 查看与文件

打开 Open Design，选择上述独立项目，在 Design Files 中打开 `desktop.html` 或 `mobile.html`。

本目录包含相同 HTML 设计资产和 OpenDesign 导出的图：

- `desktop.html`：电脑紧凑树与原保存位置入口。
- `mobile.html`：手机全屏分层，提供层级树切换。
- `desktop.png`：1440×1000 导出。
- `mobile.png`：390×844 导出。

原始设计依据已复制到 OpenDesign 项目内的 `DOWNLOAD_PATH_TREE_DESIGN.md`，原文未修改。

## 覆盖与交互

两稿均有状态选择器：已选中、无授权、无权限/授权变化、加载中、离线、只读。后五种停用确认并展示原因；可重试恢复示例状态。目录行选择同步页脚路径；取消/关闭保持父表单原值；“使用此目录”只回填草稿并提示尚未保存、下载或移动。手机行高56px，按钮至少44px；固定底部保留 `env(safe-area-inset-bottom)`。

所有路径与权限显式标为示例，不读取 NAS；HTML 无 fetch/业务请求，不安装软件、不读凭据、不改变账号、不修改 RPanel 或其它 profile，不做产品实现、构建、打包或 git 操作。

## 已验证与边界

- OpenDesign 项目、文件创建成功并读回；原生导出 PNG 成功。
- 两张最终导出图视觉检查：树/当前层、完整路径、选中提示和底部按钮均出现，无明显重叠裁切。
- `node --check` 通过；Node VM 对两稿实际运行脚本，初始渲染、五类禁用状态、取消不改值、确认只改草稿、手机树切换均 PASS。
- 这不是产品功能验收；未验证 NAS 权限、物理手机 safe-area 或完整键盘焦点陷阱。树箭头/导航是设计模拟，不是真实文件系统。
- WSL computer_use 实际只列到 Linux 应用，不能直接代表 Windows 安装状态。另通过 PowerShell 查实 Windows Open Design 进程及其监听服务。当前该 daemon 的项目列表初始为空；在用户工程常见位置作有限层级查找未定位 RPanel，因此未能引用既有 RPanel 文档。没有把此局部查找当成 RPanel 不存在的结论，也没有为查找它扫描秘密或其它个人内容。
- 官方能力依据：https://github.com/nexu-io/open-design 及当前安装包内 CLI/MCP/API 源码。该版支持 project create/list/info、MCP create_artifact/write_file/create_project、HTML/图片等导出。本次未修改任何 MCP 客户端配置。
