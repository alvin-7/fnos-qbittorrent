# fnOS qBittorrent 产品设计 v1.0-confirmed

用户已授权实施。最终确认：官方开源 qBittorrent 5.2.x（本轮锁定 5.2.4）；**重新制作飞牛风格简洁响应式 UI，不以原生 UI 交付**；仅 x86_64；明天用户自行真实 NAS 验收。开发环境仅 WSL 隔离数据，无 NAS 访问授权。

## 产品与主线
fnOS 安装 → 打开自定义登录页 → qB 账号认证 → 手机卡片/桌面表格任务管理 → 添加磁链或种子 → 查看进度/文件/速度 → 停止/开始 → 确认删除（默认保留文件）→ 重启保持任务。

## 设计决定及合理默认
- React/TypeScript/Vite 自定义 alternate WebUI，由 qB 本身同源提供页面与 `/api/v2/`，不增加代理，不绕过认证、CSRF 或 Host 检查。
- UI 中文，浅色蓝白、圆角、清晰层级；桌面侧栏/表格，手机单列卡片，触控目标≥44px；空态/加载/失败/会话过期/无搜索结果必须可辨。
- 登录不保存明文密码；首次使用官方临时密码机制（日志只在管理员本机查看），登录后提供账号/密码设置。没有固定通用密码。
- 应用 ID `fnos-qbittorrent`、显示名「轻下载 · qBittorrent」、Web 端口 18080、BT 端口 6881，时区 Asia/Shanghai。固定 Web 端口使 manifest/入口/compose 一致；不做未经验证的动态端口入口。
- 默认下载使用应用声明共享目录；容器内 `/downloads`，临时目录 `/downloads/incomplete`。界面路径为容器路径，不能任意访问 NAS 全盘。
- 镜像官方来源 https://github.com/qbittorrent/docker-qbittorrent-nox ，锁定 tag + digest、linux/amd64。不编造版本，不使用 latest。
- 普通设置仅路径、上下行限速、账号密码。复杂功能移入独立「高级设置」入口，提供重新校验、队列/连接/DHT/PeX/UPnP 等谨慎控制；无 RSS/插件/云/自动公网穿透。
- 不自动公网下载任何 torrent；验证只用本地生成合法测试种子，DHT/PeX/LSD/UPnP 默认关闭。
- 卸载脚本不主动删除下载数据；真实 NAS 保留配置选择和平台资源删除行为列入明日检查。

## 需求与验收
|ID|confirmed 要求|可观察结果|
|---|---|---|
|REQ-FN-001|fnpack 真实构建 x86 `.fpk`|构建退出0、包结构/校验和|
|REQ-FN-002|官方 qB 5.2.4|容器 CLI 与 API 真实版本，来源 digest|
|REQ-FN-003|生命周期/入口|main start/stop/status、fnOS 安装/升级/卸载明日实测|
|REQ-FN-004|持久化|隔离容器重启后任务、设置保留；NAS ACL 明日实测|
|REQ-UI-001|桌面自定义表格 UI|真实浏览器登录→任务操作|
|REQ-UI-002|手机卡片 UI|手机 viewport 无横向溢出；真机明日实测|
|REQ-UI-003|列表筛选/搜索/磁链和种子添加/stop/start/确认删除/详情文件速度|同源 API 真实任务闭环|
|REQ-UI-004|基本限速/路径/高级设置|保存后读取回验；高级不挤占主界面|
|REQ-SEC-001|原生认证、CSRF/Host 防护、无通用密码|未授权拒绝、恶意 Origin/Host 拒绝|
|REQ-SEC-002|无凭证进入包/普通证据|产物与日志审计；临时密码仅隔离私有运行目录|
|REQ-ARCH-001|仅 x86_64|manifest x86，compose linux/amd64|
|REQ-DOC-001|许可/来源/明日验收|交付清单、GPL 追溯、测试命令/退出码|

## 范围与阶段门禁
本轮不安装到 NAS、不公开网络、不提交推送、不读取用户下载或凭证。上游全部复杂管理功能不承诺覆盖；核心需求不得用 mock 验收。代码测试、构建、真实容器集成、浏览器 viewport 与 NAS 产品验收分别报告。打包成功不等于 NAS 验收完成。docs/platform 由规范核查代理独占。
