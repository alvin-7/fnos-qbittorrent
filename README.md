# 飞牛 PT 下载

面向 fnOS 的正式命名 PT 下载应用：x86_64 原生 qBittorrent 5.2.4，PT 优先；DHT/PeX/LSD/UPnP 关闭；支持保种、限速、分享率、标签分类与 MoviePilot 入口。原创代码 GPL-3.0-or-later，署名 alvin-7。

当前正式命名版本为 **1.4.1**，对应 FPK 与完整源码包均为本地构建产物。显示名、应用 ID、gatewayPrefix、数据目录保持不变。包内发行说明明确：真实 NAS、物理手机、路径映射和完整外部发行合规尚未验收。

支持 URL（不要求 `.torrent` 后缀）/磁力/种子文件添加、状态与详情、PT 暂停/普通开始/强制开始、分享率和定时限速、分类/标签浏览与批量操作。DHT、PeX、LSD、UPnP 默认关闭；保留 private 标记，不添加公共 tracker。202 只表示接受请求，不代表下载任务已出现；失败反馈不能证明站点返回了哪种页面。

## 结构与端口边界

```text
fnOS 已鉴权入口 → 私有 Unix socket → Go gateway → 127.0.0.1:18080 qB Web API
                           └─ 可选 MoviePilot 专用监听 18081（认证 + 网络边界）
React UI → 同源 /app/fnos-qbittorrent-native/ → 允许的 API
```

- `src/`：React UI、API 调用、批处理与输入校验；`public/assets/`：品牌资源。
- `gateway/`：fnOS Unix 身份校验、同源/CSRF、安全诊断、qB 重认证与 MoviePilot 适配器。
- `native/`：配置及进程生命周期；`tools/`：构建、来源审计和隔离回归入口；`tests/`：浏览器/真实后端 fixtures。
- qB 原生运行时仍依赖 Qt、libtorrent、musl、TLS 插件及 CA；移除上游页面不等于移除 Qt 或许可证责任。
- 源码保留 Docker 历史路径 `/app/fnos-qbittorrent`；原生构建会统一替换为 `...-native`。不要只改一端。
- `package.json` 的 1.0.0 是历史 UI 工作区版本，不是 FPK 版本；旧 staging manifest 也不是当前发行元数据。

## 开发与验证

需要 Node（Vite 7 要求兼容版本）、npm、Go、Python 3。真实浏览器测试另需 Google Chrome；Docker 客户端集成需 Docker。使用 PATH 中工具，不依赖某个开发者 home。

```bash
npm ci
npm run build
GO111MODULE=off go test -race ./gateway ./native
GO111MODULE=off go vet ./gateway ./native
node tools/test_selection140.mjs
node tools/test_label_batch130.mjs
node tools/test_labels130.mjs
node tools/test_connector134_validation.mjs
```

`npm run build` 是通用 UI 编译；原生编译使用 `VITE_NATIVE=1 npm run build`，FPK 工具随后转换前缀。`tools/build_ui.py` 生成 public/private 两棵通用 alternate WebUI；不会单独生成原生安装包。Go 代码使用标准库，历史布局没有 go.mod，测试时显式关闭 module 模式。

真实 **最终包** iframe/qB 回归（必须已有本地 `.runtime/package140`，不会凭空下载或伪造运行时）：

```bash
SELECTION_PACKAGE=140 python3 tools/verify_selection140_real.py
python3 tools/verify_regression140.py
CONNECTOR_TEST_BIND=<本机可达的测试接口地址> python3 tools/verify_connector140_real.py
```

这些入口仅用于隔离开发环境：会监听固定本地端口、创建专用测试进程/容器并写入 `.runtime`/`evidence`，不可指向生产数据。端口占用应停止而不是终止未知进程。`npm test` 是历史 Docker fixture 测试集，不等于无需服务的单元测试。

## 原生构建与复现边界

干净源码应用编译入口：`python3 tools/build_checkout.py`，不读取历史 FPK，可生成原生前缀 UI/gateway/native-control 并执行测试；不生成 qB 运行时或完整 FPK。部分上游输入可用 `tools/fetch_native_inputs.py` 按 `docs/NATIVE_INPUTS.lock.json` 获取并校验。完整原生构建仍 **blocked**，不得称为可复现。

`python3 tools/build_native_1_4_0.py` 是 **不可变历史候选构建入口**，不是一键从空仓库构建：依赖 1.3.9 FPK、`release/native-1.1.4-sources`、本地 fnpack 和运行时输入；已有输出时拒绝覆盖。详见 [源码交付](docs/SOURCE_DELIVERY.md)。不要为试运行删除旧包或工作目录。Git checkout 只包含审阅后的源码，不携带数 GB 运行时/源码归档；不能宣称完整离线复现。旧工具原路径保留，见 [工具索引](tools/README.md)。

## 使用及 MoviePilot

安装前核对 FPK 和同版本源码包的 SHA256；通过 fnOS 应用入口打开，由平台先鉴权。不要将测试身份注入 HTTP bridge 部署到 NAS。内核密码由应用私密文件管理，不向 MoviePilot 复用。

MoviePilot 在高级设置中单独启用，设置用户名/密码和专用端口，再测试真实客户端登录并读取 qB 状态。**18081 是可选自动化 API，不是 BT 端口，也不是 18080 管理端口。** 同 NAS Docker 可使用 `host.docker.internal`，但该名称是客户端路由而不是 bind 地址；Linux 下必须确认 host alias 与实际可达接口。当前默认监听所有 IPv4 接口 `0.0.0.0`，按用户确认的低摩擦 LAN 模式以 NAS 防火墙为网络边界，不提供 CIDR 或业务 API allowlist。认证者可操作完整 qB 业务 API（包括删除任务/文件和修改偏好），不是只读或细粒度授权。保留密码认证，不允许公网映射/暴露。禁用或换密撤销旧会话。密码显示只通过受保护管理界面，不在 URL、日志、issue 或截图提供凭据。

MoviePilot 保存路径必须是 **qB 所见路径**；Docker/NAS 挂载映射需真实读写验证，配置保存成功不等于路径已验收。下载为零与任务未创建是不同问题；只有确认任务存在后才排查 BT 入站端口/防火墙，不开放管理端口作为 PT 修复。

## 安全与许可证

见 [SECURITY.md](SECURITY.md)、[第三方 NOTICE](THIRD_PARTY_NOTICES.md)、[对应源码交付](docs/SOURCE_DELIVERY.md)。请勿上传签名 PT URL、NAS 地址、日志原件、密码配置或历史源码包；`.gitignore` 不是秘密清洗器，上传前重新扫描实际文件集合。
