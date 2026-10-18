# 下载路径树 / 选择下载目录：追加设计

- 状态：**DESIGN ONLY / 未实施 / 未验收**。本轮仅新增本文，不修改业务代码、配置、旧设计，不构建 FPK，不提交/push，不访问 NAS。
- 源码审计基点：`12721ed6fb3064335de8e52a0cda82c5d2562a51` 工作区；以下行号对应本轮读取的源码，不代表已安装包或线上事实。
- 追加关系：补充 `UI_REDESIGN_OPENDESIGN.md`、`LABEL_CATEGORY_MOBILE_OPENDESIGN.md`，不覆盖它们；历史文档的旧行号/旧状态不作为当前源码依据。
- OpenDesign：本轮没有可调用的 OpenDesign 设计工具，未假称调用。采用手机优先、可审查状态与交互契约，以文本线框形成可评审基线。
- 用户已确认的约束：**路径树只能显示飞牛 App 已授予本应用访问权限的目录；其它目录完全不返回、不展示，不列宿主根/整卷后灰置。OS 可读不等于 fnOS 已授权。** 此项不是待选建议。

## 1. 结论与范围

复用一个 `DownloadDirectoryPicker`（提议名称），为添加任务保存位置、默认下载路径、临时下载目录、分类保存路径提供真实 NAS 目录选择。**用户目的只是更方便选下载目录，不是文件管理器或权限管理器。** 主流程固定为：原保存路径输入框旁“选择目录” → 仅已授权目录 → 选中 → “使用此目录”回填原表单。电脑默认紧凑目录树；树 + 右侧当前层子目录仅保留为宽屏可评审备选，不增加工具栏/模式切换负担；手机默认全屏分层浏览，保留“层级树”入口。

目录源必须由服务端读取真实文件系统，并先取得 fnOS 针对本应用的实际授权集合，再做当前用户 ACL 与包 UID 实际访问检查。浏览器文件选择器、任务文件列表、默认路径、最近路径均不能生成授权树。

**核对结果与常见误区相反：qB 5.2.4 确实有 `app/getDirectoryContent`，不是没有 filesystem 能力。** 但它不提供 fnOS 授权根约束、受控分页和本设计的权限契约；不应把它直接透传为选择器。推荐新增管理员保护的 gateway 私有只读 browse 服务，自行受限枚举。它是安全适配层，不是伪造 qB API。

### 本轮不做

- 不改变已有任务位置，不提供 `torrents/setLocation` 或搬文件；详情中保存位置仍为只读信息。
- 不自动保存父表单、不自动添加任务、不自动修改分类或默认路径。
- 不自动创建不存在目录；“新建文件夹”仅为 proposed 的后续独立写能力。
- 不遍历全 NAS，不读文件内容、文件名称列表、私有配置、私有日志，不递归扫描。
- 不把 MoviePilot 透明 API 变成私有目录浏览通道。
- 不自动申请或扩大授权；授权管理仍是明确的独立系统操作。

## 2. 实际代码审计与影响

| 证据 | 当前事实 | 本设计处理 |
|---|---|---|
| `src/AddTask.tsx:6-21,25-29,57-73` | 原生保存位置从空值开始，读取 `app/preferences.save_path`，`edited` 防晚到默认覆盖编辑；路径仅校验绝对路径/控制字符；字段 `savepath` 发往 `torrents/add` | 输入旁加“选择目录”；选择只更新草稿并标记 edited；保留默认加载/错误与既有提交观察，不冒充目录已授权 |
| `src/Settings.tsx:6,9,17-21,27-28` | `allowedPath` 将 native 的 `prefs.save_path` 当边界；默认/临时目录必须在该值之下；保存设置将 `temp_path_enabled` 设 true，并读回 preferences | 这是字符串边界，不是授权发现；会误拒其它已授权根，也不能挡 symlink。设计替换为服务端授权校验；选择器不负责开关临时目录，不改保存范围 |
| `src/Labels.tsx:5-15,18-22` | 分类资源显示 `savePath`；管理区有自由路径输入、创建/编辑分类；空或绝对路径检查；auto-TMM 任务风险有前端阻止；写入后回读分类 | 路径标签仍只读；仅管理表单接入选择器；空值保留“由 qB 策略决定”，不能被默认根替换；服务端也需保护 auto-TMM 风险 |
| `src/tags.ts:1,23-26` | `Category.savePath` 来源为 qB categories | 分类配置不等于 NAS 实际授权或目录存在 |
| `gateway/gateway_native.go:14-17,38-53,81-105,114-128` | Unix 连接上下文 + 单一 fnOS UID/admin 身份、浏览器来源及非简单请求标记；GET 路由有 allowlist | 新 browse 必须放在同等鉴权之后；不能仅凭请求伪造 X-Trim 身份，也不能把公共 CSRF marker 当凭据 |
| `gateway/gateway_native.go:20-27,119-125` | `app/getDirectoryContent` 不在 native GET allowlist；POST 不是同一读 allowlist | 不能声称 upstream browse 所有方法已被阻止；必须审计并阻断直接 browse 的替代入口 |
| `gateway/native.go:80-119` | 后端认证预检，限制 auth 与 WebUI preferences；没有 fnOS 根级路径策略 | 现有 gateway 并没有本设计所需授权路径校验，不得称“权限已完成” |
| `gateway/proxy.go:124-140` | native 入口在鉴权后路由 connector 管理，其余进入 qB proxy | 私有 browse 应在此类鉴权后、qB proxy 前单独分发；不得传入 qB Transport |
| `gateway/connector.go:425-429,497-515,532-549` | MoviePilot connector 按 `/api/v2/<group>/<action>` 语法透明转发；只排除 connector/diagnostics/auth 组，并非业务端点 allowlist | 当前语法边界可能允许 upstream `app/getDirectoryContent`。这是源码风险，不是实测已泄露；新私有路由须放在 `/api/v2` 外，并另行显式封住 upstream browse GET/POST/别名绕过 |
| `native/control.go:25-33,67-75` | 拒绝 root、核对 TRIM_UID；只接受一个不含 `:` 的绝对 `TRIM_DATA_SHARE_PATHS`；启动准备会创建 incomplete 并做写探针；子进程继承环境 | **当前 lifecycle 单根**，未消费动态授权 API 或 ACCESSIBLE 列表；现有 prepare 写探针不能复制到只读 browse 中 |
| `tools/build_native.py:29-30`；本地 `native-package/config/resource:1` / `config/privilege:1` | 声明一个 `fnos-qbittorrent-native/downloads` share；包用户 qb-native，run-as=package | 本地包配置佐证单 share，不等于真实 NAS 授权清单；不得据此猜测 `/vol1/...` 或声称已支持多根 |

## 3. fnOS 授权来源：已核实与平台阻塞

### 3.1 官方来源

本轮检索了以下官方文档，未调用真实 NAS 接口：

1. [应用资源](https://developer.fnnas.com/docs/core-concepts/resource/)：`data-share.shares` 声明共享目录，系统为应用运行用户赋予 **Windows ACL**；`TRIM_DATA_SHARE_PATHS` 给出创建后的真实路径；share 软链可指向这些路径。不是 POSIX ACL 配置方案。
2. [环境变量](https://developer.fnnas.com/docs/core-concepts/environment-variables)：SHARE 是资源声明路径；`TRIM_DATA_ACCESSIBLE_PATHS` 是用户授权可访问路径；均可用 `:` 分隔多路径。变量是启动上下文，不保证长运行进程实时更新撤销授权。
3. [共享授权路径](https://developer.fnnas.com/api/authorization/shared-access)：服务端 `trim.file.getSharedAccessibleFolders`，请求固定本应用 appName、data `{}`，成功响应 `code:0,data:{paths:[...]}`；scope `trim.file.sharedAccess`。管理员在飞牛应用设置授权目录，SDK 授权是可选独立流程。
4. [文件权限检查](https://developer.fnnas.com/api/authorization/file-acl)：`trim.file.checkUserACL`，scope `trim.file.userAcl`；data 为可信当前用户 uid 和 path/path[]；返回 readable/writable/deletable。**检查用户权限不等于为应用授权**。
5. [调用方式](https://developer.fnnas.com/api/calling)：服务端经 Unix socket `/var/run/trim_open_gateway_apiscope.socket` 调 `POST /api/v1/trimapp`，Bearer 从当前进程 `TRIM_API_TOKEN` 取，不落盘、不返回浏览器；scope 在 resource 声明。SDK 需要 `micro_app=true`，本轮不引入 SDK。

共享查询与用户 ACL 文档要求 fnOS `1.2.0401` / 飞牛 App `1.34.0`；这是**平台版本要求，不是本应用版本号**。目标 NAS/手机实际版本、scope、socket、token 是否可用尚未核验。

### 3.2 确认采用的授权模型

- 根来源两类：A. fnOS 实际兑现的本包 data-share（资源与运行环境交叉核验）；B. fnOS 当前 `getSharedAccessibleFolders` 为固定本应用返回的授权目录。
- `TRIM_DATA_ACCESSIBLE_PATHS` 作为来源核对和启动快照，不作为动态撤权后的永久通行证；不得从 `prefs.save_path`、分类路径、localStorage、挂载表、`os.ReadDir("/")`、`/vol1` 扫描补根。
- roots 返回值是当前已确认授权集合中、当前用户可读且包用户可访问的目录；读写只读状态另列。未授权或当前用户不可读的条目**完全省略**，不返回其名称、路径、数量、灰置占位或不可见子项计数。
- 系统确认授予整卷时可按真实授权处理；不能因卷存在就列卷，也不默认请求整卷授权。多卷显示为独立授权根，不增加可选的“NAS /”父目录。
- A/B realpath 相同可合并展示并保留双来源；嵌套根保留独立 rootId 及来源，避免将窄根扩大为其父目录。rootId 由服务端映射，不由客户端传绝对根决定。
- browse/validate 每次使用当前授权视图，失败立即 fail closed；确认选择与业务提交再次刷新授权与 ACL。缓存不可延长已撤销授权。保留竞态说明：平台检查与实际 qB 写入之间无法凭一次检查承诺永久授权。

### 3.3 支持范围和 block 条件

现有代码与声明只证实“一条应用声明 share + lifecycle 单根限制”；它**不能发现飞牛 App 后续授权的其它目录**。多根 UI 是目标设计，不是既有能力。未来实现需适配上述真实 API、scope 和 lifecycle 多路径解析，不能只改 UI。

完整模式必须成功查询动态列表，结合资源根校验及当前用户 ACL。若平台版本不符、token/scope/socket 不可用、响应无法确认、无法安全检查当前用户权限，进入 `BLOCKED_AUTH_SOURCE`，不显示推测树、不退化全盘浏览。可解释“当前平台无法核实本应用授权目录，请检查系统版本/应用授权后重试”。**单根资源模式也仅是可研究的受限兼容方案，尚未获准实施或验收**；不能在动态列表失效时静默启用，更不能把环境快照说成完整实时列表。

手动输入同样不能绕过 block。原有表单值可以保留为“历史配置，未验证”，但不能在新增选择器流程里当作已授权目录使用。

## 4. qB 5.2.4 能力核对与隔离

官方固定 tag 源码：

- [appcontroller.h](https://github.com/qbittorrent/qBittorrent/blob/release-5.2.4/src/webui/api/appcontroller.h)：声明 `getDirectoryContentAction()`。
- [appcontroller.cpp](https://github.com/qbittorrent/qBittorrent/blob/release-5.2.4/src/webui/api/appcontroller.cpp)：`AppController::getDirectoryContentAction` 接收必需 `dirPath`，要求非空绝对路径且存在；mode 为 all/dirs/files，默认 all；withMetadata 可选；QDirIterator 无递归参数，枚举当前层并形成整个数组。

结论：端点为 `/api/v2/app/getDirectoryContent`，有真实单层目录读取能力；但默认可能列文件，源码没有 fnOS 根约束、分页或当前 fnOS 用户 ACL。`torrents/files` 是任务内文件，不是目录浏览；`app/defaultSavePath` 也不是授权发现。这里只做固定版本源码核对，**没有对真实运行中的 5.2.4 发起端点测试**。

目标链路：

```text
手机 / 电脑
  → fnOS 原生统一网关（可信 Unix ingress + 当前管理员身份 + 来源/CSRF）
    → 私有 directory handler
      → fnOS 授权 API + 当前用户 ACL
      → 包 UID 下受限真实文件系统单层枚举
  ← 最少目录信息（不含未授权条目）

MoviePilot TCP connector → qB 业务透明 API
  × 不可到达私有 directory handler
  × 不可用 upstream getDirectoryContent 绕过私有浏览隔离
```

新路由使用 `/app/fnos-qbittorrent-native/gateway/directories/...`（proposed），明确不在 `/api/v2/<group>/<action>`。应提炼或复用鉴权逻辑后分流，不应先分流再鉴权。还需在透明 connector 与 native qB 通道显式拒绝 upstream browse 的所有支持方法；仅藏 UI/仅 GET allowlist 不够。这是后续安全实施门槛，本轮没有改变现有透明 API 行为，不声称已封堵。

## 5. 可复用组件与调用方语义

### 5.1 组件边界（proposed contract）

```ts
// 仅设计契约，不是已添加的业务代码
DownloadDirectoryPicker({
  purpose: 'add-save' | 'default-save' | 'temp-download' | 'category-save',
  initialPath: string,
  onConfirm: (choice: { rootId: string; canonicalPath: string;
    authorizationRevision: string; checkedAt: string }) => void,
  onCancel: () => void
})
```

组件只负责授权根/目录导航、选中草稿、校验与返回；不调用 add/setPreferences/createCategory/editCategory/setLocation。`authorizationRevision` 不是写权限令牌，不能跳过提交时重新检查。父表单负责持有草稿、dirty 状态、明确业务提交与既有读回。

| 调用场景 | 确认选择之后 | 业务提交与副作用边界 |
|---|---|---|
| 添加任务保存位置 | 更新 `savepath` 草稿，标记用户已编辑 | 用户点击“开始添加”才 POST torrents/add；服务端再验授权；不改变其它任务 |
| 默认下载路径 | 仅更新 `save_path` 草稿 | 点击保存才 setPreferences + preferences 回读；先评估 auto-TMM，可能影响既有任务时阻止保存而非承诺绝不移动 |
| 临时下载目录 | 仅更新 `temp_path` 草稿 | 不因选择而启用临时目录；父表单保持/明确启用开关；有进行中任务且影响未证明安全时阻止相关保存 |
| 分类保存路径 | 更新 `savePath` 草稿；显式“由 qB 默认策略决定”可清为空 | 点击创建/保存分类才写 + categories 回读；有受影响 auto-TMM 任务必须服务端阻止；不默默改 TMM 设置 |

默认/分类路径变化可能通过 qB 策略触发搬移，不能因为不调用 setLocation 就宣称没有风险。后续开发应读取相关 preferences 与 torrents/info；遇未知风险 fail closed。对改变既有任务位置的确认/迁移方案另立设计，不在本轮追加一个“确认搬移”按钮放行。

## 6. 桌面与手机交互

线框中的“授权目录 A / 电影 / 4K”为**示意布局标签，不是 NAS 返回数据或预置假树**。运行时仅渲染服务端已核实结果。

### 6.1 电脑：轻量紧凑树主方案

```text
原表单：保存位置 [现有路径________________] [选择目录]

┌ 选择下载目录                              关闭 × ┐
│ 仅显示本应用已授权目录                           │
│ [返回上一级] 授权目录 A > 电影                    │
│ ▾ 授权目录 A                                    │
│   ▾ 电影                 ✓ 当前选中             │
│     ▸ 4K                                        │
│     ▸ 剧集                                      │
│ ▸ 授权目录 B                                    │
│ 当前完整路径：<服务端确认的授权根>/电影           │
│ 仅回填原表单             [取消] [使用此目录]      │
└─────────────────────────────────────────────────┘
```

输入仍在原表单直接粘贴，进入选择器时服务端校验定位；不再为此增加独立的文件地址工具栏。加载更多只在确实有分页时显示，刷新仅用于错误恢复/授权变化。无需文件搜索、预览、排序工具、批量操作或权限配置。

以下双栏仅记录最初要求的宽屏备选线框，**不是默认实现或必须交付的复杂工具**；其“最近使用”等附加项不进入轻量首轮基线：

```text
┌ 选择下载目录 · 添加任务保存位置                         关闭 × ┐
│ 仅显示飞牛已授予本应用访问权限的目录          [刷新授权状态] │
│ [返回上一级]  授权目录 A > 电影 > 4K                      │
├─────────────────────┬──────────────────────────────────┤
│ 已授权目录           │ 当前目录的子目录                  │
│ ▾ 授权目录 A         │ ▸ 片单一                     进入 │
│   ▾ 电影             │ ▸ 片单二                     进入 │
│     ● 4K [已选中]    │                                  │
│ ▸ 授权目录 B         │ [加载更多]（非递归）              │
│ [最近使用：需再校验] │                                  │
├─────────────────────┴──────────────────────────────────┤
│ 当前完整路径：<服务端确认的授权根绝对路径>/电影/4K       │
│ [粘贴路径…]     应用可写 / 当前用户可写 · 刚刚核验       │
│ 仅填回表单，不会保存设置或移动任务       [取消] [使用此目录]│
└────────────────────────────────────────────────────────┘
```

- 默认紧凑树；双栏仅为非基线宽屏备选，不要求实现模式切换。始终保留面包屑、完整路径、固定底部按钮。
- 展开箭头只加载该节点一层；选中行高亮同时有图标/文本，不靠颜色。进入目录将该目录设为当前候选，父目录也可选。
- 没读过子层时用“展开/进入”，不要递归探测 hasChildren；空层返回后才提示无子目录。
- 面包屑仅从授权根开始，没有可点击的宿主 `/`、卷父路径；多根入口叫“已授权目录”，不是一个可被选择的物理父目录。

### 6.2 手机：全屏分层浏览（主流程）

```text
┌ ← 返回        选择下载目录           关闭 × ┐
│ 临时下载目录                              │
│ [已授权目录] > 授权目录 A > 电影           │
│ [层级树]                    [刷新]        │
├──────────────────────────────────────────┤
│ 当前：电影                ✓ 已选中         │
│ 📁 4K                                 ›  │
│ 📁 剧集                               ›  │
│ [加载更多]                               │
│                                          │
├──────────────────────────────────────────┤
│ 当前完整路径：<真实授权根>/电影            │
│ [粘贴路径并校验]                          │
│ 仅填回路径，不会保存或移动任务             │
│ [取消]                     [使用此目录]   │
└──────────────────────────────────────────┘
```

- 返回在子层回父层，在根层回“已授权目录”；系统返回/关闭离开选择器而不丢父表单。记忆每层滚动位置与加载页。
- “层级树”打开全屏内的树视图/子页，只展示授权根和已按需加载节点；选节点返回层级浏览，不扫描其它分支。不能用只有列表无树入口的实现宣称完成路径树。
- 顶栏关闭与底栏确认固定，避让 safe-area 与软键盘；44px 触控区，长路径换行、完整值可查看/复制但不横向撑屏。面包屑可折叠中间层，展开祖先列表仅含根内祖先。
- 读写权限不足、加载中、失效时禁用确认且给可见原因；无子目录时仍可选当前可写目录。
- 嵌套弹层需焦点陷阱；Esc/取消恢复触发按钮焦点；点击内容空白不关闭；桌面仅 backdrop 本体可取消，手机不依赖 backdrop。树支持上下/Home/End、左右展开/收起，使用 aria-expanded/aria-selected；加载/错误分别 status/alert。

### 6.3 手动路径与最近目录

粘贴路径保留在原保存路径输入框，打开选择器定位或点击父表单提交时进行同一服务端校验，不要求增加独立地址管理工具。只在服务端确认属于当前授权集合、存在、为目录且可读后建立候选；用户粘贴内容不能被回显错误扩展成宿主路径探测器。越界/未知路径统一“目录不可用或未授权”，不区分隐藏目标是否存在。不存在路径不自动 mkdir，不把浏览器本机路径映射到 NAS。

最近目录仅为可清除的安全本地偏好，建议默认关闭、用户开启后最多 5 条，仅存 rootId/相对定位信息，不上传、不跨账号/NAS混用；按应用实例与当前用户隔离，退出/换账号可清除。不存 token、ACL、整棵树。每次展示名称/使用前重新校验授权；失效项删除，不渲染为根。即使本地被篡改也不能拓展服务端根。确认/取消不改变授权，最近目录永远不是授权来源。

## 7. 状态机与异步一致性

```text
CLOSED --打开--> ROOTS_LOADING
ROOTS_LOADING --成功且有根--> ROOTS_READY
              --成功但无可展示根--> NO_AUTHORIZED_ROOT
              --来源/ACL不可核实--> BLOCKED_AUTH_SOURCE
ROOTS_READY --进入目录--> LAYER_LOADING --成功--> BROWSING / EMPTY_LAYER
                                        --失败--> LAYER_ERROR
BROWSING --选中/进入/粘贴--> VALIDATING --可读可写--> CANDIDATE_READY
                                     --只读--> READ_ONLY
                                     --未知/越界/失效--> INVALID
CANDIDATE_READY --使用此目录--> REVALIDATING --成功--> CONFIRMED → CLOSED
                                           --撤权/离线/变更--> INVALID
任意打开状态 --取消/关闭--> CLOSED（不触发业务写入）
任意读状态 --刷新授权--> ROOTS_LOADING（清除失效候选与旧缓存）
```

- 展开与路径请求带 requestId/generation；切根/关闭取消旧请求，晚响应不得覆盖当前目录或恢复撤权内容。缓存键含用户、应用、授权 revision、rootId、相对路径、cursor；只放会话内。
- 加载新层先清除可确认状态；确认只对应当前高亮路径，不能让页脚路径与树高亮不一致。确认期间防双击，成功只回调一次。
- 失败保留父表单草稿，不自动选择第一个目录、不自动重放写入。业务保存失败与“目录已选中”分开显示。
- 空根：“未找到可用的已授权目录，请在飞牛应用设置检查授权后刷新”；不暗示目录为空盘。只读仍可进入已授权可读目录，但不能作为写入目的地确认。

## 8. 私有只读接口契约（全部 proposed）

统一前缀 `/app/fnos-qbittorrent-native/gateway/directories`。为避免把路径写入查询 URL/访问日志，使用 POST JSON 承载只读请求；**POST 不代表写文件**。只读权限边界、CSRF/来源检查、速率限制依然必须执行，不走 qB API 客户端透明前缀拼接。所有响应 `Cache-Control:no-store`，无 CORS，拒绝 OPTIONS。

| 路由 | 请求 | 成功响应要点 |
|---|---|---|
| `/roots` | `{}`；appName/uid 不由浏览器指定 | `{authorizationRevision,roots:[{rootId,label,canonicalPath,source:['resource'|'sharedGrant'],readable:true,writable,state:'online'|'offline'}]}`；只含已确认授权且用户可读条目 |
| `/browse` | `{rootId,relativePath:'电影',cursor:null,limit:100,authorizationRevision}` | `{rootId,relativePath,canonicalPath,breadcrumbs,entries:[{name,relativePath,kind:'directory',writable}],nextCursor:null,authorizationRevision}` |
| `/validate` | `{purpose,rootId,relativePath,authorizationRevision}` 或互斥 `{purpose,manualPath}` | `{rootId,canonicalPath,relativePath,readable:true,writable:true,authorizationRevision,checkedAt}`；不保存/创建/移动 |

- roots 的 offline 状态只能来自仍可确认授权和可披露的根元数据；若无法确认权限可披露性则省略或全局 blocked，不靠读取离线盘探测生成列表。
- browse 可显示已授权且当前用户可读但不可写的子目录，明确只读；未授权或不可读目录连名称也不返回；越界 symlink 不返回。目录条目无文件 size/mtime/文件数量，亦不返回隐藏条目总数。
- `relativePath` 是服务端原样返回的相对定位符；rootId 仅是引用，不是授权 token；canonicalPath 仅在校验通过后输出。面包屑由授权根内的已校验层级生成。
- limit 默认 100、最大 200（设计预算，待性能确认）；cursor 不透明且签名/服务端状态绑定用户、根、目录、revision、短时限，防篡改与跨根重放。nextCursor 为 null 才表示本轮遍历结束，不提供未经遍历证实的总数。
- 错误结构 `{code,retryable,requestId}`，固定前端中文映射，无原始 OS error/绝对越界路径/平台 token。401/403 鉴权；400 INVALID_REQUEST；404 DIRECTORY_UNAVAILABLE（隐藏不存在/未授权差别）；409 AUTHORIZATION_CHANGED 或 CURSOR_EXPIRED；422 READ_ONLY；429 RATE_LIMITED；503 AUTH_SOURCE_UNAVAILABLE/MOUNT_UNAVAILABLE；504 BROWSE_TIMEOUT。精细离线原因仅在已授权目标上披露。

### 单层大目录分页与预算

每次只处理当前层，不做 Walk/WalkDir/rglob，不为了树箭头扫描子层；只对当前批次候选做目录类型与权限判定，跳过普通文件，不读取内容。推荐受限服务端目录迭代会话，按文件系统迭代顺序分页（不承诺全目录字母排序），每批权限过滤后至多返回 limit 个目录；可有空 entries 但有 nextCursor，UI 提示“继续读取”，不得当作目录已空。

每请求还需限制已扫描条目数、执行时间、总响应字节、路径深度/字节长度、并发、目录句柄/游标会话与TTL；不能只限制返回条目数。建议起始预算：3 秒、扫描 2000 项、256 KiB、每用户 2 个浏览请求、32 个游标会话、60 秒TTL；数值均待压测，不是已测指标。达到预算返回继续游标或固定超时，不在后台无界补扫。重试读请求需用户操作/有界策略，不影响任务业务提交。

目录内容并发变化可能导致枚举重复/漏项，客户端按真实定位符去重并提供刷新；不承诺快照一致排序。离线网络挂载的系统调用可能不响应 Go context，需证明可中断隔离 worker/有界队列及并发回收；若不能界定资源占用则作为发布 blocker，而非只设置 HTTP timeout 便宣称可控。

## 9. 安全与文件系统约束

1. **三道门**：fnOS 对本应用确实授权 → 可信当前管理员 uid 的 fnOS ACL 可读/可写 → qb-native 包 UID 的系统实际访问权限。缺一不可；管理员会话不赋予全盘权，POSIX mode 位不代替 Windows ACL。
2. roots 只从可信资源/系统授权来源产生；不接受浏览器提交 rootPath/appName/uid。业务 add/preferences/category 也需再次执行路径约束，不能只验 picker，否则手动输入/直接 API 可绕过。
3. 对根和目标逐段规范化并 realpath containment；按路径段而非字符串 startsWith（`share2` 不是 `share` 子目录）。拒绝 `..`、绝对 relativePath、NUL/CR/LF、非法编码；禁止多重 URL decode，明确 JSON 路径语义，合法名称中的 `%` 不擅自二次解码。
4. 根的官方 share 别名可经可信来源 realpath 映射；任一子链接 realpath 越出该 root 授权边界则隐藏/拒绝，即使另一根授权目标也不通过该链接跳转，需从另一根进入。断链、循环、链接到文件不展示。授权根被替换、链接目标/挂载身份变化使 revision/缓存失效，重新核实来源而非追随新目标。
5. realpath 先验有 TOCTOU 风险：受限枚举用目录 FD 相对遍历，适配 Linux openat2 RESOLVE_BENEATH/NO_MAGICLINKS 或等价安全逐段方案，防链接替换、proc magic link；不可仅先 EvalSymlinks 再任意路径打开。确认与业务转发再次校验；qB 自身随后写入仍需 ACL 与受控权限，不宣称完全消除 qB 写入竞态。
6. 授权根内的子挂载也不能自动扩展授权边界：跨设备/挂载点须确认平台授权确实覆盖目标，否则隐藏/拒绝；卷离线不回落到同路径挂载点下面的宿主空目录，不自动 mkdir。
7. 不把应用私有数据/log/profile/runtime 作为下载根或树项；即使平台误配置到宽路径也需要保守排除已知私有目录（其余未授权条目无条件隐藏），不能读取私有日志来推断根。
8. Unicode/中文/emoji 路径按真实字节标识保留，不 trim 目录名、不大小写折叠、不 NFC/NFD 改写；仅展示排序可 locale 化。双向文本/控制显示用安全转义与隔离，不修改实际路径。无法无损表示的文件系统名称拒绝选择并给固定说明；React 文本转义防 XSS。
9. 写能力判断不依赖 browse 创建探针；结合当前用户 ACL 与包用户实际访问检查返回 writable/unknown，unknown 禁用确认。存在且可写不保证剩余空间或未来下载成功，错误不能承诺已验证下载。
10. 日志仅 reason/requestId/阶段与耗时，不记录目录名称、绝对路径、请求体、token、原始 fnOS/OS 错误；禁用这组接口的 URL/body 调试打印。限流失败也不能打印私有目录。

## 10. 需求 ID 与验收矩阵

以下均为**未来验收计划，NOT RUN**；文档结构检查不等于功能验收。

| ID | 需求/验证方法 | 通过标准 | 本轮状态 |
|---|---|---|---|
| DPT-01 | 真实 fnOS 多授权根；放一个 OS 可读但未授权目录 | roots/tree 不含该未授权名称、路径、占位、数量；不是列卷后灰置 | 未实施/未验收 |
| DPT-02 | 资源 share、ACCESSIBLE 快照、动态 API 核对 | 明确当前单根限制；动态授权根出现；授权撤回后立即失效，不从 prefs/recent 补根 | 未实施/平台待核验 |
| DPT-03 | socket/token/scope/版本失败或 ACL 无法确认 | blocked，无全盘/缓存快照降级，粘贴不能绕过 | 未实施/未验收 |
| DPT-04 | 电脑紧凑树实操（双栏非基线备选） | 展开单层，面包屑/上一级/完整路径/高亮/明确确认齐全；可选父目录 | 未实施/未验收 |
| DPT-05 | 真实手机 fnOS iframe 及窄屏浏览器 | 全屏分层 + 层级树入口；44px/安全区/长路径/键盘/返回/关闭无丢表单 | 未实施/需物理机 |
| DPT-06 | 四种 purpose 打开、选中、取消 | 只填对应草稿；picker 网络零业务 mutation；取消父值不变；分类空继承独立 | 未实施/未验收 |
| DPT-07 | 新任务、默认/临时、分类各自明确提交 | 再校验授权；add 观察真实 hash；preferences/categories 回读；不串字段 | 未实施/未验收 |
| DPT-08 | 已有任务/auto-TMM 下改默认/临时/分类路径 | 有搬移风险或未知则阻止；零 setLocation、零已有任务搬移，不改 TMM 策略 | 未实施/未验收 |
| DPT-09 | 链接越界/断链/循环/父路径穿越/前缀同名 | 不返回越界链接，粘贴统一拒绝，竞态替换/跨挂载不逃逸 | 未实施/未验收 |
| DPT-10 | 仅当前用户不可读、包 UID 不可写、Windows ACL 只读 | 隐藏不可读；只读可浏览但不可确认；不以 root/POSIX mode 绕过 | 未实施/需 NAS ACL |
| DPT-11 | 多卷/相同 realpath/嵌套授权/挂载离线 | 不补卷父级；准确合并/保留边界；离线不进入挂载点宿主后备目录 | 未实施/需 NAS |
| DPT-12 | 超大单层（含大量文件）、深树、慢挂载 | 分页预算/去重/游标TTL/取消/超时有界；无递归、无文件内容读取 | 未实施/需压测 |
| DPT-13 | 中文/空格/emoji/组合字符/%/双向字符 | 原值往返，安全显示；不 trim/NFC，合法路径不破坏；非法输入安全拒绝 | 未实施/未验收 |
| DPT-14 | 新私有路径的 TCP/伪 X-Trim/非管理员/跨站/无 marker | 403/404，零目录披露；正常 Unix 管理员来源才可用 | 未实施/未验收 |
| DPT-15 | MoviePilot 已登录后请求私有 browse 和 upstream getDirectoryContent GET/POST/编码变体 | 均不能获取目录；正常 qB 业务兼容另测；不能仅藏前端入口 | 未实施/现有风险待封堵 |
| DPT-16 | 手动不存在/未授权/晚到响应/关闭重开/重复点击 | 统一拒绝、不建目录、不泄露存在性；旧响应不覆盖；确认回调一次 | 未实施/未验收 |
| DPT-17 | 篡改最近路径/换用户/换NAS/撤权 | 本地偏好不扩权，未经校验不展示，清除可用、不上传 | 未实施/未验收 |
| DPT-18 | 空根/空层/只读/超时/错误 UI 与日志审计 | 有可恢复状态、确认禁用原因；无原始日志/文件名/平台token泄露 | 未实施/未验收 |
| DPT-19 | 新建文件夹 | 基线无创建按钮/API；若未来另批需独立写权限/显式确认/防重放/回读 | proposed，不属基线 |

## 11. 待决策与实施门槛

### 已确认，不再作为选项

- 只显示本应用已授权目录；其它目录完全不返回不展示；OS 可读不是授权。
- 手机全屏分层 + 树入口，电脑树；真实服务端单层懒加载。
- 只选址，不搬已有任务，不 setLocation；新建文件夹非默认；最近目录非授权根。

### 需要决策/证据

| 编号 | 项目 | 建议/阻塞条件 |
|---|---|---|
| DEC-01 | 目标 NAS/App 是否满足官方 API 版本、scope、token/socket 与 ACL | 必须实机只读验证；不可用则完整模式 blocked，不退化全盘；兼容单根模式需另行批准 |
| DEC-02 | 声明 share 是否包含在动态查询结果、授权撤销/缓存/子挂载语义 | 官方文档未保证全部行为，实机交叉验证；差集不能猜测授权，宁可阻止 |
| DEC-03 | 新增 sharedAccess/userAcl scopes 与是否提供授权管理入口 | 最小 scope；本轮只查/选，授权默认引导飞牛应用设置；SDK 属后续独立范围 |
| DEC-04 | 多根 lifecycle 迁移 | 当前 prepare 单根需独立方案；不得改默认路径/写探针遍历全部新授权根 |
| DEC-05 | 大目录顺序、资源预算与慢挂载隔离 | 优先无全量排序的迭代分页，预算压测后冻结；无法中断占用则不发布 |
| DEC-06 | upstream browse 透明 API 封堵与兼容影响 | 安全硬门槛；确认所有请求方法与编码变体，单独回归 MoviePilot 普通业务；不维持私有浏览透传 |
| DEC-07 | 默认/临时路径已有任务影响判定 | 对 qB 5.2.4 安全策略做隔离真实运行验证，未知时阻止相关保存；不扩张成迁移功能 |
| DEC-08 | 后续 mkdir 与最近目录默认值 | mkdir 需新设计独立写接口/父目录权限/单次确认/创建读回；最近目录建议默认关闭 |

## 12. 本轮交付与限制

已完成静态源码、包配置与官方固定版本/平台文档审计，并形成追加设计。未实施目录组件、授权发现、分页、安全拦截或业务校验；未跑功能用例、未连接真实 NAS、未验 ACL/多卷/物理手机，不能标为通过验收。当前上游目录端点存在与透明 connector 语法风险均来自源码，不是现场漏洞利用结论。本文不修改任何既有设计、不产出包、不发布。
