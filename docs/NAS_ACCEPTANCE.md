# 明日真 NAS 手动验收（测试版，尚未认证 fnOS 兼容）

## 安装前
- 仅 x86_64；记录 fnOS 版本、CPU、浏览器/手机型号。不要安装到含重要任务的旧 qB 应用上；本包独立 ID `fnos-qbittorrent`。
- 文件：`release/fnos-qbittorrent-1.0.6-x86_64.fpk`，同目录 SHA256SUMS。请先核对校验和。
- 需要 fnOS Docker 应用/服务正常并能访问 ghcr.io。FPK 不内含 110 MB 内核镜像，安装会从官方 registry 拉取固定 digest。
- 18080/TCP 为管理端口，6881/TCP+UDP 为 BT。检查无冲突；不要配置公网端口转发。HTTP 只用于可信局域网；跨不可信网络应先设置受信 HTTPS 反代，不能禁用 CSRF/Host 防护。
- 1.0.6 的 UI 使用相对静态资源路径，并根据当前 URL 是否位于 `/app/fnos-qbittorrent` 构造 API 路径；因此同一构建同时支持 `http://NAS:18080/` 和统一网关入口。网关仅代理 `/app/fnos-qbittorrent` 及其子路径，不暴露 NAS 根 `/assets` 或 `/api`。

- 统一网关硬门禁：入口 ID `fnos-qbittorrent.Application`，`protocol` 为空，`gatewayPrefix=/app/fnos-qbittorrent`、`gatewaySocket=app.sock`、`url=/app/fnos-qbittorrent`；网关将 NAS 登录态请求转发至长期运行的 Unix Socket。18080 仅绑定本机供代理访问，不作为公网入口。
- 设置页不提供安装密码、密码变更或退出按钮；安装/运行时 qB 继续生成和提供临时密码，密码不得写入日志。
- 非回环来源未登录预期为 `401`；登录后读取和 `app/setPreferences` 写入成功。错误 Host 或不可信 Origin 仍预期为 `401/403`。

### 认证边界验收
1. `127.0.0.1:18080` 的 `/api/v2/app/version` 和任务读取应为 `200`，自定义 UI 直接显示任务入口。
2. 从桥接容器或 NAS 的局域网地址访问时，未登录 API 应为 `401`，UI 应显示登录页；使用安装/运行时 qB 提供的账号和临时密码登录后，任务读取、设置读取及 `app/setPreferences` POST 应成功。
3. 错误 Host、错误 Origin/CSRF 请求保持 `401/403`；不得为绕过认证关闭 Host/CSRF。
4. 不记录密码、Cookie 或带签名查询参数。真实 NAS、飞牛 App 统一网关和手机入口需按本节手工验收；本地容器通过不代表 NAS 已验收。
2. 安装/配置/升级后检查配置中的 `WebUI\\ServerDomains`：必须包含 `localhost`、`127.0.0.1` 和当前 NAS 的 RFC1918 IPv4；填写的域名追加；已有自定义条目和密码保持。更换 DHCP 地址后再次启动或配置，旧自动地址移除、新地址出现。
3. 从飞牛应用卡片打开：这是本修复的硬门禁，必须显示「轻下载」而非空白；检查开发者工具网络请求中的 HTML、JS/CSS 和 API 均带 `/app/fnos-qbittorrent/` 前缀且为 200（不应请求 NAS 根 `/assets` 或 `/api`）。确认入口 ID `fnos-qbittorrent.Application`、`desktop_uidir=ui`、`type=iframe`、`protocol=http`、`port=18080`、`url=/`，且包内 `app/ui/config` 与 `app/ui/images/icon_64.png` 存在。若仍空白，记录 App/系统版本、入口错误日志和 WebView 网络请求；优先排查 iframe 对外部端口限制，按官方网关方案改为 `gatewayPrefix=/app/qbittorrent`、`gatewaySocket=app.sock` 的 NAS 实测兼容入口，不能以本机 Chrome 结果替代。
4. 直接访问 `http://NAS地址:18080/` 及错误 Host 验证：正确地址正常，错误 Host 仍 `401`；确认 Host 校验与 CSRF 仍开启。

- 空态 → 添加项目内 `tests/fixtures/legal-test.torrent` 或自己有权获取的种子；合法测试文件见项目隔离测试，不会公网下载。可另选公开授权大文件做真实带宽验收，需用户自行决定。
- 添加任务必须支持三种来源：输入 `magnet:?` 磁力链接、输入任意合法 `http://`/`https://` BT 下载链接（仅可信来源，不要求 `.torrent` 后缀），或上传本地 `.torrent`；前两者通过 qB `torrents/add` 的 `urls` 字段。
- 查看任务表格（桌面）/卡片（手机），名称、状态、进度、上下行速度。
- 搜索不存在名称显示无匹配；状态筛选；暂停应已暂停、继续应恢复。
- 详情查看文件、路径、大小、进度、速度；高级任务信息可重新校验。
- 添加合法磁链；「添加后保持暂停」可避免启动下载，确认任务出现后删除。
- 删除前必须弹确认，默认不勾选同时删除文件；取消不删除；确认后在文件管理器检查下载数据仍在。勾选删除文件仅使用可丢弃测试数据验证。
- 设置限速为 2048/512 KiB/s，关闭重开确认；0 为不限速。路径必须用容器内 `/downloads` 或子目录。
- 高级入口独立，DHT/PeX/LSD/UPnP 初始关闭；不要为测试随意开启公网发现/映射。

## 生命周期/权限
- 下载共享目录应出现在 `fnos-qbittorrent/downloads`，不要修改全盘权限。容器以应用 TRIM_UID/GID 非 root 运行；验证 ACL 写入、共享文件读取、临时目录和磁盘剩余空间。
- 应用中心停止 → 状态未运行；启动 → 状态运行、入口可达。
- 带任务和设置重启应用/NAS，检查恢复。
- 安装相同测试包做覆盖升级，先备份配置；检查账号、任务、限速、下载文件保持。
- 卸载时选择保留数据，应用脚本不删除下载。**fnOS 平台卸载资源行为尚未实机验证**；先备份，仅在可丢弃数据上做卸载/重装测试。

## 手机与异常
- 竖屏/横屏，360~430px 浏览器；检查无横向滚动、文件选择器可用、键盘不遮挡提交、滚动弹层、返回关闭。
- 错误密码、退出后访问 API、断网/服务停止、端口占用、共享目录拒绝写入均应有可诊断错误。
- 若启动失败：应用中心错误日志 + 容器退出码 + fnOS 版本。请去除临时密码、Cookie、Token、真实文件名后再分享。
- 若返回 401/403：先核对访问来源是否在 RFC1918/回环白名单、Host 是否为向导填写的准确地址、Origin 是否可信；不要关闭 Host/CSRF 校验，也不要添加公网网段。管理员可在停用应用后更新 qB 配置中的 `WebUI\\ServerDomains`（Qt INI 值需整体加引号，分号分隔），再启动。

## 通过标准
安装/启动/正式入口免密码/任务添加/操作/路径与限速/手机主线/重启持久化/ACL/升级保留全部通过才称 NAS 验收通过。账号密码变更和退出不属于方案A。
