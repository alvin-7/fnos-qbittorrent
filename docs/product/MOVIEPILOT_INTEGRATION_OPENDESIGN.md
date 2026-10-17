# MoviePilot 连接与标签/分类集成 OpenDesign

- **文档版本**：v0.2.0
- **设计状态**：OpenDesign v0.2 / 用户已确认并授权进入实施；本任务仅更新设计，实施另派任务；尚未实现、未监听、未验收
- **基线**：native 1.2.8；原生 qBittorrent 5.2.4 x86_64；目标 qB Web API 2.x
- **创建日期**：2026-10-16
- **适用入口**：custom fnOS UI 唯一人机入口；MoviePilot 独立标准 HTTP qB 机器入口
- **明确禁止**：本阶段不修改 `src/`、`gateway/`、`native/`、`manifest`，不改 qB 配置，不访问真实 NAS，不生成或更新 FPK

> 本文是实现前的设计基线，不是已实现功能的声明。源码中已经出现的标签辅助代码均按“未验收/待审计”处理。

## 1. 产品目标与非目标

### 1.1 目标

1. 为 PT 优先用户提供可理解的“分类 + 标签”工作流：分类承担保存路径/自动化路由，标签承担筛选、标记和 MoviePilot 业务关联。
2. MoviePilot 与 qBittorrent 之间只通过标准 qB Web API 建立可审计连接；所有写操作都读回 qB 的真实状态后才显示成功。
3. 支持资源 CRUD、添加任务时赋值、单任务/批量任务赋值、筛选和空态，并在桌面与手机端保持同一状态语义。
4. 保留现有安全边界：qB 仅回环管理端口、Host/CSRF 校验开启、DHT/PeX/LSD/UPnP 按 PT 约束关闭；fnOS 统一网关是浏览器入口。
5. 将 MoviePilot 接入设计为受控的内部能力，而不是把某个端口、浏览器网关或前端假状态冒充 MoviePilot 连接。

### 1.2 非目标

- 不在 UI 中实现 MoviePilot 本身，不复制其数据库、媒体库、用户权限或自动化引擎。
- 不让浏览器直接访问 `127.0.0.1:18080`、`49160`，也不把 BT 监听端口当管理 API 端口。
- 不让 MoviePilot 直接调用 fnOS 浏览器统一网关；浏览器网关服务的是已认证的人机入口，不是后端到后端集成协议。
- 不修改 qB 原生内核、API 语义、PT 私有标志、发现协议或 NAT/防火墙。
- 不在标签/分类删除时删除任务、数据文件或保存目录。
- 不以 mock、前端 local state、HTTP 202 或“请求已发出”作为成功证据。
- 不在本阶段打包、安装、提交、推送或操作真实 NAS。

## 2. 现状审计与证据边界

### 2.1 已读基线

- 现有 UI 设计基线：`docs/product/UI_REDESIGN_OPENDESIGN.md`。
- 当前前端涉及文件：`src/tags.ts`、`src/api.ts`、`src/AddTask.tsx`，以及任务列表/详情/设置页面。
- 当前版本证据：`evidence/native-package-audit-1.2.8.json`、`evidence/native-1.2.8-verification.json`、`evidence/qb524-torrentscontroller.cpp`、`evidence/qb524-appcontroller.cpp`。
- 官方 qB 5.0+ Web API 文档明确 API 形式为 `/api/v2/{scope}/{method}`，读用 GET、写用 POST，API 需要认证；添加任务支持 `category` 与逗号分隔的 `tags`。[1]
- qB 5.2.4 官方源码分支包含 `setCategory`, `createCategory`, `editCategory`, `removeCategories`, `addTags`, `setTags`, `removeTags`, `createTags`, `deleteTags`, `categories`, `tags` 控制器动作；`torrents/info` 序列化分类字段并按标签过滤。[2]
- qB 5.2.4 `app/preferences` 暴露分类路径自动管理相关偏好，以及 WebUI 地址/端口、Host、CSRF、认证和反向代理安全设置。[3]
- qB WebApplication 源码显示会话 cookie 名称带 WebUI 端口后缀，API 按认证会话分发，Host/域名、CSRF、点击劫持等是 WebUI 的安全边界。[4]
- qB 官方 release 页面列出 `release-5.2.4`，本项目将该版本作为固定运行基线。[5]

### 2.2 当前标签代码：未验收/待审计

当前已发现 `src/tags.ts`，它包含标签校验、`torrents/categories`/`torrents/tags` 读取，以及通过 `setCategory`、`removeTags`、`addTags` 写入并再次调用 `torrents/info` 的辅助函数；`AddTask.tsx` 也读取分类/标签字段。

这**不等于功能已完成**，原因是本设计阶段尚未完成以下审计：

- 尚未证明所有入口均从最终 custom UI 经过正式 fnOS 网关；
- 尚未证明 qB 5.2.4 实例中每一条端点和返回体都可用；
- 尚未证明分类/标签 CRUD、删除保护、批量一致性、读回和重启持久化；
- 尚未证明写入失败、权限拒绝、网络中断时没有业务重放；
- 尚未证明 MoviePilot 后端接入边界存在，更没有证明连接真实可用；
- 尚未证明桌面/手机线框对应实现，也没有本轮的最终包级证据。

因此需求矩阵中的实现状态统一为 `implemented_unverified` 或 `pending`，不得标记 `verified`。

## 3. MoviePilot 连接拓扑与安全边界

### 3.1 已收敛拓扑与配置

本节以 `MOVIEPILOT_CONNECTOR_OPENDESIGN.md` v0.2.0 为连接器详细设计；用户已授权后续独立任务进入实施，本任务仅设计落盘、未实现。

**用户已确认**：MoviePilot 是同一台 NAS 的 Docker 容器，已通过 `host.docker.internal` 访问宿主。无需再询问 Docker 模式/地址。

```text
MoviePilot 标准 qB 客户端
  → http://host.docker.internal:18081（示例；18081 proposed，未实现/未监听）
  → 独立 HTTP Connector（实际宿主接口 IP + 明确来源 CIDR）
  → 受控 backend 认证/白名单代理
  → qB 5.2.4 127.0.0.1:18080 → 真实状态
```

`host.docker.internal` 是容器 DNS 别名，不能作为宿主 bind IP。后续实施探测其解析目标、实际 Docker 宿主可达接口、来源 NAT/CIDR、18081 占用和防火墙；不假定容器访问宿主 loopback，不默认绑定 0.0.0.0/:: 或允许所有 RFC1918，不凭空写固定网段。bridge 的 127.0.0.1 是容器自身，host network 共享宿主网络；二者地址不可混用，此说明不是要求用户再次确认拓扑。

内部 18080 不公开，BT 49160 不混用；浏览器仍通过 fnOS 统一网关/应用 Unix ingress → custom UI，与 MoviePilot 认证和会话分离。Unix socket 不作为 MoviePilot 下载器地址。

HTTP 传输实际为明文，仅限可信 NAS 内网/容器网络；不可信网络必须 TLS 和经过验证的反代/来源边界，否则不启用。

高级设置默认关闭；启用须账号、密码、可配置端口、实际监听 IP、允许来源。先安全只读发现候选与最小范围，预填草稿供确认，不要求用户手填所有未知信息，不擅自扩大范围。提供脱敏参数复制、只读测试与配置/listener/backend/容器端分项状态；保存确认和 backend 读回矩阵见连接器 §9.1。

### 3.2 明确禁止的“连接”

| 方案 | 结论 | 原因 |
|---|---|---|
| MoviePilot → `127.0.0.1:18080` | 禁止作为产品契约 | 这是 qB 内部回环管理端口，不是可跨服务假定可达的 MoviePilot 入口；直接放开会扩大攻击面 |
| MoviePilot → `49160` | 禁止 | 这是 BT peer 监听端口，不是 HTTP Web API；不能读写分类、标签或偏好 |
| MoviePilot → 浏览器/fnOS 网关 URL | 禁止 | 该入口绑定人机登录态、Origin、Fetch Metadata、CSRF 和应用会话；不能让后端伪造浏览器身份 |
| MoviePilot → 前端 local state | 禁止 | 不产生 qB 持久化状态，不能作为真实连接或成功证明 |
| MoviePilot → 未限制的 LAN/public reverse proxy | 禁止 | 会将 qB 管理能力暴露到不必要的网络边界，并绕开产品的单一入口约束 |

### 3.3 安全门禁

实现前必须由平台/部署设计确认以下门禁：

1. **进程身份**：Connector/代理/qB UID/GID、私有凭据 ACL 和 MoviePilot 挂载身份需验证；浏览器内部 Unix ingress 最小权限不变，不将 socket 共享作为 MoviePilot 接入条件。
2. **传输边界**：标准 HTTP 独立入口绑定实际宿主可达 IP、明确来源 CIDR；18081 proposed 待冲突检测，可信内网外必须 TLS，无公网映射、禁止任意 Host 转发。
3. **路径 allowlist**：代理只允许设计矩阵中的 qB API；默认拒绝日志、Cookie 管理、关机、任意 preferences 写入、文件系统浏览等非集成功能。
4. **方法 allowlist**：GET 只读；POST 只允许明确的分类/标签/任务添加及必要的读回，不将 GET 当作写操作许可。
5. **认证**：Connector 使用独立的受控 qB 服务凭据/会话，不读取浏览器 Cookie，不把密码放 URL、静态前端、日志或 MoviePilot 配置明文输出。qB 登录后必须用 `/api/v2/app/version` 或同等受保护读接口验证。
6. **CSRF/Host**：qB 原生 Host/CSRF 保持开启。代理向 qB 发请求时使用固定、可验证的内部 authority；不得用任意外部 Host 覆盖安全校验。
7. **来源约束**：浏览器的 session token、`X-Fnos-CSRF`、Origin/Referer 仅属于 fnOS UI 路径，不能转交 MoviePilot。
8. **响应过滤**：不向 MoviePilot 返回 qB SID、密码、Cookie、下载 URL 查询串、tracker passkey、原始日志或路径中可识别的秘密。
9. **超时与 no-replay**：超时或连接断开后状态为“未确认”；禁止自动重发业务写请求。必须先 GET 读回或由用户明确重新操作。
10. **审计**：记录时间、固定 operation ID、端点、hash 数量和安全 reason code；不记录 URL、标签中的敏感业务内容、凭据或 SID。
11. **生命周期**：qB/代理重启、socket 替换、UID 变化、凭据失效均使连接进入 `backend_unavailable` 或 `reauth_required`，不得静默降级为假成功。
12. **平台验收**：本地/loopback 通过不等于 NAS 容器通过；须独立验收实际绑定、来源 CIDR、host.docker.internal 入口可达、统一网关边界、路径映射和无公网暴露。

## 4. API 契约逐项映射

### 4.1 统一规则

- 真实基地址由受控 Connector 注入；UI 只使用现有正式网关 API 客户端，不能拼接 `18080` 或 `49160`。
- 读请求可 GET；所有状态改变使用 POST 和表单编码。
- `hashes` 使用 qB 约定的 `|` 分隔；`tags`/`categories` 使用 qB 端点约定的逗号或换行语义时，必须按端点单独编码，不能把原文拼到 URL。
- 每个 mutation 结果至少分为：`accepted`（服务端返回）、`confirmed`（目标读回匹配）、`unconfirmed`（连接/超时/部分失败）。UI 只有 `confirmed` 显示成功。
- 标签名/分类名按现有设计约束校验：非空、最多 256 Unicode code points、拒绝 NUL/CR/LF/控制字符；路径必须按 qB 语义为绝对路径或明确空值。此校验仍待与真实 qB 接受范围对照。

### 4.2 资源 CRUD 与任务 API

| 需求 ID | qB API | 方法/请求字段 | 设计语义 | 必须读回 |
|---|---|---|---|---|
| API-CAT-01 | `torrents/categories` | GET，无参数 | 读取分类映射；名称、`savePath` 为后端事实 | 分类列表与路径 |
| API-CAT-02 | `torrents/createCategory` | POST `category`, `savePath`；可选下载路径字段需以 5.2.4 实测为准 | 创建分类；不创建前不允许任务赋予不存在分类 | `categories` 中出现同名分类且路径一致 |
| API-CAT-03 | `torrents/editCategory` | POST `category`, `savePath`；重命名是否另有字段必须以 5.2.4 实际契约确认 | 修改分类路径/属性；若产品支持重命名，先确定 qB 5.2.4 的真实字段 | `categories` 读回名称与路径 |
| API-CAT-04 | `torrents/removeCategories` | POST `categories` | 删除分类元数据；二次确认；不得删除任务/文件 | 分类不再出现；原任务仍存在且文件未删除 |
| API-TAG-01 | `torrents/tags` | GET，无参数 | 读取标签资源 | 标签列表 |
| API-TAG-02 | `torrents/createTags` | POST `tags` | 创建一个或多个标签；UI 默认单值操作以避免逗号歧义 | `tags` 中出现目标标签 |
| API-TAG-03 | `torrents/deleteTags` | POST `tags` | 删除标签定义/关联；二次确认；不得删除任务/文件 | `tags` 不含目标；受影响任务 `info` 不含目标 |
| API-TAG-04 | `torrents/addTags` | POST `hashes`, `tags` | 给一个/多个真实 hash 添加标签 | 每个 hash 的 `torrents/info` 回读包含标签 |
| API-TAG-05 | `torrents/setTags` | POST `hashes`, `tags` | qB 5.2.4 源码存在 setTags；是否作为 MoviePilot 兼容公共契约须先实测。推荐优先使用标准 add/remove 差集，除非实测确认 setTags 语义稳定 | 每个 hash 的标签集合与目标集合完全相等 |
| API-TAG-06 | `torrents/removeTags` | POST `hashes`, `tags` | 从真实任务移除指定标签 | 每个 hash 的 `info` 回读不含标签 |
| API-TOR-01 | `torrents/add` | POST multipart/form-data；`urls` 或 `torrents`，可选 `category`, `tags`, `savepath` 等 | 添加任务时传入分类/标签；202/200 只表示请求被处理/接受 | 先观察任务 hash，再 `info` 读回 category/tags |
| API-TOR-02 | `torrents/info` | GET；`hashes` 可为 `|` 分隔，支持 `category`/`tag` 筛选 | 任务、筛选和所有写入的唯一事实来源 | 目标 hash 的完整相关字段 |
| API-APP-01 | `app/preferences` | GET | 读取 `auto_tmm_enabled`、`category_changed_tmm_enabled`、`category` 路由相关偏好；不读取/展示无关秘密字段 | 保存/路由策略的当前状态 |
| API-APP-02 | `app/setPreferences` | POST `json` | 仅在产品明确授权后配置分类路径自动管理；本轮默认不隐式改动 | `app/preferences` 读回；任务路径另行 `info` 验证 |

官方文档说明 `torrents/add` 返回 415 表示 torrent 文件无效，正常场景可返回 200；本产品仍不能把 200/202 等同于“任务已成功加入”，必须执行任务观察和字段读回。[2] qB 5.2.4 源码也显示 `setCategory` 会对不存在/不正确分类产生冲突错误，并将分类/标签动作实现为控制器动作。[2]

### 4.3 MoviePilot 客户端契约：标准 qB HTTP，不要求自定义 REST

对外沿用 `/api/v2/...` qB 路径、方法、字段与错误语义，以便 MoviePilot 现有 qB 下载器直接配置。`POST /api/v2/auth/login` 用独立专用账号/密码签发连接器自己的兼容 cookie；logout/过期/禁用/账号或密码变更/重启撤销会话。必须实测目标客户端登录及受保护 GET，不能强制 Basic、自定义认证头或让用户填写 backend 密码。

backend SID、密码和 Set-Cookie 不透传；响应过滤不得破坏 qB info 中路径/分类/标签等必要兼容字段。`operation_id/confirmed/unconfirmed` 仅供应用内部状态与审计，不强制塞入对外 qB 响应；此前拟议 `/health`、自定义 `/categories`/`/tags`/`/torrents` REST 不作为 MoviePilot 首版契约。

只读测试允许连接器 auth/login/logout POST，但业务 API 仅 GET、零 backend 业务写入；认证成功后读取实际版本、info、categories、tags。NAS 本机自测与实际容器端可达性分开，所有网络参数、端口、凭据/版本兼容均为待实施探测，不能以 UI 保存成功替代。

### 4.4 独立路径映射门禁

MoviePilot 容器路径 ↔ qB 实际 NAS 路径映射为必需验收，不等于分类 savePath。记录实际挂载/前缀映射、UID/GID 权限；授权隔离任务后从 qB info 读 save_path/content_path，检查 NAS 文件并在 MoviePilot 容器读到同一文件，验证内容/大小及整理或硬链接权限（适用时）。重启后保持；错前缀、缺挂载、权限不足必须显示失败。不得隐式移动文件、修改分类/自动管理路径；连接测试只读不代替文件验收。详见连接器 §9.2。

## 5. UI 信息架构与线框

### 5.1 信息架构

```text
应用
├─ 任务
│  ├─ 全部 / 下载中 / 做种 / 已完成
│  ├─ 分类筛选（未分类）
│  ├─ 标签筛选（未标记）
│  ├─ 任务表/卡片
│  └─ 批量操作：分类、添加标签、移除标签、清空分类
├─ 标签与分类
│  ├─ 分类列表：名称、保存路径、任务数、状态
│  ├─ 标签列表：名称、任务数、状态
│  ├─ 新建/编辑/删除
│  └─ MoviePilot 连接状态与能力
├─ 任务详情
│  ├─ 真实分类
│  ├─ 真实标签
│  ├─ 编辑标签/分类
│  └─ 后端读回时间与未确认提示
└─ 设置
   ├─ qB 连接/后端状态（只显示安全摘要）
   └─ 分类自动管理偏好（高级设置，明确影响路径）
```

### 5.2 桌面线框（1440px）

```text
┌──────────────────────────────────────────────────────────────────────┐
│ 轻下载                         [后端: 已连接] [添加任务] [设置]       │
├──────────────┬───────────────────────────────────────────────────────┤
│ 任务          │ 全部任务                    搜索…  [分类▼] [标签▼]   │
│ 标签与分类    │ ┌───────────────────────────────────────────────────┐ │
│ 设置          │ │ □ 任务名       状态   分类       标签       操作   │ │
│               │ │ □ Movie A      做种   Movies     MP,HD      …      │ │
│               │ │ □ Movie B      下载   未分类     无         …      │ │
│               │ └───────────────────────────────────────────────────┘ │
│               │ 选中 2 项：[设置分类] [添加标签] [移除标签]           │
└──────────────┴───────────────────────────────────────────────────────┘
```

原则：高频筛选和批量操作在任务页；资源 CRUD 在“标签与分类”；详情弹层显示后端事实；不显示未经读回的乐观值。

### 5.3 手机线框（390px）

```text
┌──────────────────────────────┐
│ 轻下载       ⋮  添加          │
├──────────────────────────────┤
│ [全部▼] [分类▼] [标签▼]       │
│ ┌──────────────────────────┐ │
│ │ Movie A                  │ │
│ │ 做种 · Movies            │ │
│ │ #MP  #HD                 │ │
│ │                    ⋯     │ │
│ └──────────────────────────┘ │
│ ┌──────────────────────────┐ │
│ │ Movie B                  │ │
│ │ 下载 · 未分类 · 无标签    │ │
│ └──────────────────────────┘ │
├──────────────────────────────┤
│ 任务     标签/分类     设置   │
└──────────────────────────────┘
```

手机上批量选择进入底部操作栏；所有按钮触控目标至少 44px；长文本换行；modal 的关闭按钮固定在右上安全区；加载或提交期间控件 `disabled`、`aria-busy=true`，所有成功/失败/取消路径清除 busy/pressed 状态。

### 5.4 状态模型

```text
uninitialized
  └─ loading_resources ──┬─ ready
                         ├─ no_backend
                         ├─ permission_denied
                         └─ load_failed
ready + mutation
  └─ validating → submitting → accepted → reading_back
                                      ├─ confirmed
                                      ├─ partial_failed
                                      └─ unconfirmed
```

任务列表数据与分类/标签资源分离加载：资源加载失败不能抹掉已有任务列表，但相关控件必须禁用并显示原因。写入状态按 operation 粒度管理，不能用全局“保存成功”覆盖部分失败。

## 6. 状态文案与行为

| 状态 | UI 行为 | 禁止行为 |
|---|---|---|
| loading | 骨架/状态文字；禁用重复操作 | 不显示空列表为“无任务” |
| success/confirmed | 显示 qB 读回值和时间；允许继续操作 | 不只依据 200/202 显示成功 |
| failed | 显示固定 reason code、端点、可执行建议；保留原值 | 不吞掉 qB 409/415/401/403 |
| permission_denied | 显示“无权访问/需要应用权限”；提供重新进入正式入口 | 不要求用户把 18080 暴露出来 |
| no_backend | 显示“qB 后端不可达/未配置”；MoviePilot 状态为未连接 | 不用 localStorage 假造分类/标签 |
| accepted/unconfirmed | 显示“请求已送达但结果未确认，请刷新读取”；阻止自动重试 | 不自动再次 POST |
| partial_failed | 显示成功 hash 数、失败 hash 数和逐项原因 | 不把整批标成成功 |
| delete confirm | 明确“只删元数据，不删任务/文件”或实际影响范围 | 不用含糊的“删除”直接执行 |
| empty resources | 标签/分类空态含创建入口和后端状态 | 不把资源加载失败当空态 |
| filtered empty | 显示“当前筛选无结果”，可清除筛选 | 不说“没有任务” |

## 7. 真实后端验收矩阵

所有测试必须针对隔离的真实 qBittorrent 5.2.4 x86_64，使用安全测试任务和非真实 PT URL；不接触真实 NAS 任务/凭据。每个写测试记录请求、HTTP 状态、读回和重启后的结果，但脱敏 URL、Cookie、SID 和标签业务秘密。

| 验收 ID | 场景 | 操作 | 通过条件 | 证据 |
|---|---|---|---|---|
| ACC-CONN-01 | 版本/能力 | 标准 login + qB `/app/version`, `/app/webapiVersion` | 版本为 5.2.4；能力由实测返回，不靠猜测 | 响应摘要 |
| ACC-CONN-02 | 安全入口 | 无授权访问 qB/代理/UI；错误 Host/Origin；浏览器正式入口 | 18080 不作为公开 MoviePilot 入口；错误来源拒绝；正式 UI 可进入 | 状态码/reason code |
| ACC-CONN-03 | HTTP 绑定/来源 | 容器经 host.docker.internal 请求；非允许来源请求 | 明确宿主 IP/来源 CIDR，允许来源认证可读，其他拒绝；18081 proposed 待冲突检查 | 实际 listener/来源与容器请求摘要 |
| ACC-CAT-01 | 分类读取 | GET categories | 返回真实 qB 分类映射和 savePath | 原始字段白名单快照 |
| ACC-CAT-02 | 分类 CRUD | create → readback → edit → readback → remove | 每一步与 qB 读回一致，删除不删任务/文件 | API + task/file 检查 |
| ACC-CAT-03 | 分类错误 | 空名、非法路径、重复名、不存在分类赋值 | 明确 400/409/404，UI 不显示成功 | 响应与 UI 状态 |
| ACC-TAG-01 | 标签 CRUD | create → tags readback → delete | 标签列表真实改变；删除不删任务/文件 | API + readback |
| ACC-TAG-02 | 任务标签 | 对真实 hash add/remove/set | 每个 hash info 读回与目标集合相等 | 前后 info |
| ACC-TAG-03 | 批量一致性 | 多 hash 部分成功/不存在 hash | 逐 hash 报告，不能整批假成功 | operation result |
| ACC-TOR-01 | 添加任务 | add 带 category/tags | 观察到真实 hash，info 读回字段一致 | add response + task info |
| ACC-TOR-02 | 异步/202 | add 返回 202/pending | 仅显示 accepted，直到 hash 和字段读回确认 | 时间线 |
| ACC-ERR-01 | 权限 | qB SID 失效、代理未认证、CSRF 缺失 | 固定权限错误；无业务 POST 自动重放 | 请求计数/状态码 |
| ACC-ERR-02 | 连接中断 | mutation 后断开/超时 | `unconfirmed`；不自动重试；人工刷新可读回 | 代理日志/请求计数 |
| ACC-ERR-03 | 后端停止 | qB 或 socket 停止 | no_backend；任务旧数据不被伪造清空 | UI 状态 + 服务状态 |
| ACC-PERSIST-01 | 重启持久化 | qB restart 后读分类、标签、任务 | 资源和任务标签保持真实值 | 重启前后快照 |
| ACC-UI-01 | 桌面 | 1440px 走任务筛选、详情、CRUD、错误 | 无溢出；modal 可滚动；关闭/返回正确 | 运行中截图 + 交互记录 |
| ACC-UI-02 | 手机 | 390px 同一主线 | 触控目标、底部批量栏、sticky close、busy 清理通过 | 运行中截图 + 交互记录 |
| ACC-MP-01 | MoviePilot 接口 | 仅通过标准 HTTP qB 兼容入口与明确来源 allowlist 调用 | 无浏览器 Cookie；白名单端点；读回确认 | Connector trace |
| ACC-MP-03 | 独立路径映射 | qB info 实际 NAS 文件与 MoviePilot 容器映射文件对照、权限/重启验证 | 相同文件可读且满足实际业务权限；不以分类路径或连接成功替代 | 映射/挂载/文件内容核验摘要 |
| ACC-MP-04 | 保存与撤销 | 启用取消/确认、修改网络或密码、禁用、重开设置 | 配置/listener/backend 逐项读回；旧会话失效，失败不扩大范围 | 连接器 §9.1 矩阵证据 |
| ACC-MP-02 | 安全负向 | 尝试 18080/49160/浏览器网关/任意 qB endpoint | 全部被拒绝或不可达，且无端口暴露 | 网络监听/拒绝记录 |
| ACC-PT-01 | PT 约束回归 | 分类/标签工作流前后检查 DHT/PeX/LSD/UPnP | 仍为关闭；BT 端口与管理端口不混淆 | preferences readback |

未完成真实后端验收前，不得使用“MoviePilot 已连接”“标签已完成”“分类功能已完成”等产品措辞。

## 8. 需求追踪矩阵

状态枚举：`pending`、`in_progress`、`implemented_unverified`、`verified`、`blocked`、`deferred`。

| ID | 需求 | 来源/证据 | 当前状态 | 实施阶段 | 验收 |
|---|---|---|---|---|---|
| MP-OBJ-01 | MoviePilot 仅通过标准 qB API 管理真实任务 | 用户约束；[1][2] | pending | P0 | ACC-MP-01 |
| MP-SEC-01 | 不使用 18080/49160/浏览器网关冒充后端入口 | 用户约束；本设计 §3 | pending | P0 | ACC-MP-02 |
| MP-SEC-02 | 标准 HTTP qB 兼容入口、明确宿主 IP/来源 CIDR | 本设计 §3.1/3.3 | pending | P0 | ACC-CONN-03 |
| MP-SEC-03 | qB Host/CSRF/认证保持开启 | [3][4]；现有网关证据 | pending | P0 | ACC-CONN-02/ERR-01 |
| API-CAT-01..04 | 分类 CRUD 与读回 | [1][2] | implemented_unverified | P1 | ACC-CAT-01..03 |
| API-TAG-01..06 | 标签 CRUD、set/add/remove 与读回 | [1][2] | implemented_unverified | P1 | ACC-TAG-01..03 |
| API-TOR-01..02 | 添加/读取任务分类标签 | [1][2] | implemented_unverified | P1 | ACC-TOR-01..02 |
| API-APP-01..02 | 偏好读取/受控写入 | [1][3] | pending | P2 | ACC-PT-01/PERSIST-01 |
| UI-IA-01 | 任务/资源/详情/设置信息架构 | 现有 UI OpenDesign；本设计 §5 | pending | P2 | ACC-UI-01/02 |
| UI-STATE-01 | loading/success/failure/permission/no-backend/未确认 | 本设计 §5/6 | pending | P2 | ACC-ERR-01..03 |
| UI-MOBILE-01 | 390px 手机主线和 44px 控件 | 现有 UI skill 约束；本设计 §5 | pending | P2 | ACC-UI-02 |
| VERIFY-01 | 真 qB 5.2.4 逐项后端验收 | 用户约束；本设计 §7 | pending | P3 | 全矩阵 |
| VERIFY-02 | 重启持久化与 no-replay | 现有 qB skill/网关证据 | pending | P3 | ACC-PERSIST-01/ERR-02 |
| SCOPE-01 | 不改 src/gateway/native/manifest、不打包 | 本轮用户明确要求 | verified（本设计阶段） | P0 | 工作区差异审计 |

## 9. 分阶段实施计划与阶段门禁

### P0 — 连接与安全设计落地

- 冻结标准 HTTP qB 契约、已确认同 NAS Docker/host.docker.internal 拓扑；实施探测真实绑定 IP/来源/端口，确定凭据 ACL、端点/方法 allowlist。
- 明确 MoviePilot 实际运行方式、客户端版本和凭据交付方式（拓扑已确认，不再重复询问）。
- 门禁：所有未决安全决策关闭；完成 ACC-CONN-01..03；没有公开管理端口。

### P1 — qB 标签/分类真实 API 垂直切片

- 先实现资源读取和任务 info 读回，再实现单项 CRUD，再实现任务赋值和批量。
- 每个 mutation 都实现 `accepted → reading_back → confirmed/unconfirmed`。
- 先针对真实 qB 5.2.4 验证 `setTags`，未验证前使用标准 add/remove 差集，不把源码存在当作兼容性证明。
- 门禁：ACC-CAT-*、ACC-TAG-*、ACC-TOR-* 通过；无 mock 作为最终证据。

### P2 — UI 主线与错误语义

- 按 §5 设计任务筛选、资源管理、详情和手机批量交互。
- 接入权限、无后端、超时、部分失败、删除确认和未确认状态。
- 门禁：ACC-UI-*、ACC-ERR-*；旧功能回归不受影响。

### P3 — MoviePilot Connector 集成

- 仅在 P0/P1 通过后接入 MoviePilot；实现内部 API 的字段白名单、限流、审计和 no-replay。
- 用隔离 MoviePilot 测试身份调用，不使用真实用户任务/凭据。
- 门禁：ACC-MP-01/02；读写均在 qB 读回后确认。

### P4 — 发布前收拢

- 从正式 custom fnOS UI 入口分别验证桌面、390px 手机、直连拒绝和统一网关路径。
- 重新审计需求矩阵、源码差异、包版本和证据；本设计阶段不执行此阶段。
- 门禁：所有必需需求 `verified`，否则保留 `blocked`/`implemented_unverified`，不得发布。

## 10. 未决决策

1. **连接形态已确定**：同 NAS Docker，经 host.docker.internal 的标准 HTTP qB 入口；18081 proposed。实际宿主绑定 IP/来源 CIDR/端口冲突与容器端可达性待实施探测，不再要求用户确认模式/地址。
2. **MoviePilot 版本与契约**：目标 MoviePilot 版本、其 qB 下载器适配器接口、需要兼容的字段和错误语义尚未锁定。
3. **凭据归属**：Connector 使用独立 qB 服务凭据、一次性启动注入，还是由应用生命周期控制器托管？禁止直接复用浏览器 SID，待安全评审确认。
4. **分类重命名语义**：qB 5.2.4 `editCategory` 的真实字段是否支持 rename；若不支持，产品是“新建+迁移+删除”还是延期？
5. **`setTags` 兼容级别**：源码存在不代表部署链路已实测；需决定 MoviePilot 契约使用 setTags，还是固定用 add/remove 差集。
6. **分类路径策略**：MoviePilot 是否拥有分类保存路径的写权限？是否允许 Connector 改变 `app/preferences` 的自动管理偏好？默认不允许隐式改动。
7. **批量原子性**：qB 端点通常不是事务；产品采用逐 hash 结果、失败重试由用户触发，还是增加受控补偿读写？默认逐 hash 报告且不自动重放。
8. **标签逗号语义**：qB 标准端点以逗号分隔标签；是否允许产品标签名含逗号需以 5.2.4 实测和 MoviePilot 互操作结果决定。当前设计建议禁止逗号或单值编码，不宣称可保留。
9. **UI 入口已确定**：高级设置配置连接器，默认关闭；资源页仅状态摘要；安全发现候选、脱敏参数复制与只读测试，保存确认/后端读回按连接器 §9.1。
10. **NAS 平台验收**：真实 fnOS 网关 authority、socket ACL、桌面 WebView 和物理手机尚未提供，均不能由本地浏览器证据替代。

## 11. 设计证据与来源

项目内证据：

- `docs/product/UI_REDESIGN_OPENDESIGN.md`
- `src/tags.ts`、`src/api.ts`、`src/AddTask.tsx`（现状审计，未验收）
- `evidence/qb524-torrentscontroller.cpp`
- `evidence/qb524-appcontroller.cpp`
- `evidence/native-1.2.8-verification.json`
- `evidence/native-package-audit-1.2.8.json`

外部来源：

[1] qBittorrent WebUI API 5.0+：API 认证、GET/POST 规则、`torrents/add`、分类/标签端点与返回语义。
[2] qBittorrent `release-5.2.4` `torrentscontroller.cpp`：5.2.4 实际控制器动作、分类/标签参数和 `torrents/info` 序列化。
[3] qBittorrent `release-5.2.4` `appcontroller.cpp`：preferences 与 WebUI/分类自动管理字段。
[4] qBittorrent `release-5.2.4` `webapplication.cpp`：会话、API 分发、替代 WebUI、Host/CSRF/安全响应边界。
[5] qBittorrent `release-5.2.4` 官方 release 页面：固定版本基线。

## 12. 本阶段结论

- 设计文档已建立，路径为 `docs/product/MOVIEPILOT_INTEGRATION_OPENDESIGN.md`。
- 现有标签辅助代码已记录为 `implemented_unverified/待审计`，没有据此宣称功能完成。
- MoviePilot 必须新增受控的服务到服务入口；采用标准 HTTP qB 兼容代理，示例 http://host.docker.internal:18081（proposed），实际宿主 IP/来源 CIDR 待实施探测；18080、49160、浏览器网关均不得冒充该入口。
- 本轮没有实现代码、没有改 `src/gateway/native/manifest`、没有打包、没有访问真实 NAS。
- 用户已授权进入独立实施任务；§10 中实际绑定/来源/端口/权限等由实施探测完成，§7 与连接器 §9 矩阵仍是启用/交付门禁；本任务不实施、不打包、不访问 NAS。

## Sources

[1] https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-%28qBittorrent-5.0%29
[2] https://raw.githubusercontent.com/qbittorrent/qBittorrent/release-5.2.4/src/webui/api/torrentscontroller.cpp
[3] https://raw.githubusercontent.com/qbittorrent/qBittorrent/release-5.2.4/src/webui/api/appcontroller.cpp
[4] https://raw.githubusercontent.com/qbittorrent/qBittorrent/release-5.2.4/src/webui/webapplication.cpp
[5] https://github.com/qbittorrent/qBittorrent/releases/tag/release-5.2.4
