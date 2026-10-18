# qBpanel 启发的飞牛 PT 工作空间重设计

## 交付边界与真实状态

- **设计成果，不是产品版本**。产品基线 native 1.5.3 / qBittorrent 5.2.4。本次只新增本文件与 `docs/design/qbpanel-inspired/`，不改 src、gateway、native、workflow，不打包 FPK、不提交/推送、不访问 NAS。
- 已在正在运行的 **Windows Open Design 0.25.0** 创建独立项目 `fnos-pt-workspace-redesign`，不是旧目录 picker 项目的覆盖稿。
- 制作方式：原创 HTML/CSS/JS 经 OpenDesign 本地 API 注册为 artifact，有 manifest、版本记录、真实本地文件并经其导出接口生成 PNG。**API 编写/注册不等于 OpenDesign 内置 AI 生成，本次未使用其内置 AI。**
- 所有任务、容量、Tracker、MoviePilot 地址、路径都是示例；不读取 NAS，不执行下载，不向业务服务发送请求。
- `AUTH_PACKAGE_READ_DENIED` **未修复**。只读审查指出：父路径逐级 `O_RDONLY | O_DIRECTORY` 可能对“父目录只允许遍历、子目录已授权”的情况过度要求读取权限；不能称实现方向完全正确，不能简单归责为用户未授权。原型保留失败和不可确认状态。

## 参考取证与授权

### qBpanel

官方仓库：<https://github.com/Smi13zZ/qbpanel>

本次实际读取的 shallow clone commit：`71ab0b9a3d837dc5c8813b461a390f5e3b87928b`。这只是取证时仓库返回的快照，不以 README 中的发布日期推断当前事实。

已读：
- `README.md`：功能矩阵、桌面/390px 手机截图引用、任务/设置/手机使用说明。
- `LICENSE`：**MIT License，Copyright (c) 2026 Smi13zZ**。若复制软件或实质片段，须保留版权/许可声明。本稿不复制其源码、品牌、Logo 或图标，截图仅在 scratch 中分析，不作为交付素材。
- `qbpanel/app/web/index.html`：实际桌面表格及手机 `tcards` 分离模板，任务名进入详情、暂停/删除按钮、复选框、多种布局。
- `qbpanel/app/web/js/app.js`：`openDetail` / `onDetailTab` / `loadProps` / `loadFiles` / `loadTrackers`、添加任务 busy/失败处理。
- 实际查看图片：`docs/images/torrents.png`、`docs/images/mobile-torrents.png`。桌面为左侧模块导航和多字段表格；手机有独立卡片，但顶部工具较多、抽屉入口较隐蔽，删除与暂停并排易误触。
- README 没有发现公开在线 demo 链接；没有编造在线演示访问成功。未启动参考项目后端，也未接入其下载器。

### Apple 官方视觉参考

已实际检索并读取官方 <https://developer.apple.com/videos/play/wwdc2025/219/>（Meet Liquid Glass），其官方原则包括：玻璃适合导航层，不应铺满内容层；有 reduced transparency / increased contrast / reduced motion 适配。

用户的“iOS27”仅作为浮动、轻盈、圆角的审美意向。**不声称某个 iOS 27 功能已发布或被本稿复现**。本次依据可核验的 Apple 官方设计材料，而非编造版本特性。

实现不是苹果材质引擎：只有 Dock 单层 12px blur + 高不透明浅色背景，卡片/表格不透明；没有持续折射动画、视频材质或资源外链。提供设置按钮关闭 blur，并使用 `prefers-reduced-transparency` 和 `prefers-reduced-motion`；不支持透明度媒体查询的浏览器仍可手动关闭。

## 提炼与选择理由

| 参考观察 | 本稿决策 | 理由 / 取舍 |
|---|---|---|
| 概览与任务分开，查看进度需要跨页 | 工作空间顶部仅保留下载/上传/保种/空间四个摘要；手机只显示速度摘要 | 以任务为主，避免整屏统计图占据高频任务空间 |
| 名称搜索 + 状态切换是高频路径 | 搜索、状态数量与状态高亮常驻；组合分类/标签放筛选层 | 兼顾快速进入与渐进呈现，不塞全部功能同屏 |
| 桌面表格同时比较进度/速度/容量/分享率 | 桌面紧凑表格，详情同屏侧面板，300–560px 宽度可调 | 监控无需来回跳页；面板出现时表格独立横向滚动，不让整页溢出 |
| 手机已经有卡片，但依赖隐藏导航 | 手机独立卡片，底部任务/分类/标签/设置 Dock，主添加单独强调 | 单手导航可见；不把桌面表格缩成横向长图 |
| 删除直接贴近暂停 | 列表不摆删除按钮，移除在保种详情或批量菜单中，默认不删除数据 | 降低误触；暂停/移除前提醒 PT 义务，不能自动判断站点规则 |
| 详情分区按需加载 | 概况/文件/Tracker/保种四层标签 | 列表不堆低频参数；手机详情为底部层，桌面为侧面板 |
| 服务器与全局设置较多 | 完全排除服务器标签、服务器列表和实例切换 | 遵守单实例飞牛 PT 产品范围 |
| MoviePilot 与 PT 是已有产品能力 | 作为来源标签与设置独立入口；未连接显示中性/失败态 | 不丢现有能力，也不伪造联通成功 |

## 信息架构与关键路径

```
Dock
├─ 任务：摘要 → 状态/搜索/排序 → 任务列表
│  ├─ 选择 → 批量暂停/继续/添加标签/移除 → 风险确认
│  └─ 详情 → 概况 / 文件 / Tracker / 保种
├─ 分类：电影 / 剧集 / 音乐 / 软件 → 已筛选任务（高亮 chip）
├─ 标签：PT / 保种 / MoviePilot → 已筛选任务（高亮 chip）
├─ 设置：限速 / 分享率 / MoviePilot / 目录与权限 / 显示
└─ 独立 + 添加：链接或 torrent → 分类/标签/暂停 → 示例提交
   └─ 目录 picker：示例授权根 → 示例媒体 → AUTH_PACKAGE_READ_DENIED
      └─ 重试仍失败 / 上一级 / 返回（保留添加表单）
```

手机：44px 按钮最小高度、复选框包在 44×44 label 内；Dock 导航实际宽高通过浏览器测量。筛选 chips 横向滑动，内容页不是横向溢出。手机底部 sheet 使用 94dvh、内部滚动、sticky header/footer、安全区 padding、`overscroll-behavior: contain`；打开时 body scroll lock，嵌套 layer history + 返回/Escape 逐层退出，保留草稿。

桌面：侧边栏仅是快捷状态/内容筛选，Dock 承担主模块切换；不是两套竞争的服务器导航。表格 70px 双行任务行，相对手机卡片更高密度；不宣称已经验证数千任务虚拟化性能。

## 需求追踪与原型覆盖

| ID | 要求 | 对应交互 / 验证 |
|---|---|---|
| R01 | 桌面与手机新页面 | 注册 desktop.html、mobile.html，两者共享原创响应式设计，但表格/卡片和详情模式不同 |
| R02 | 任务总览/搜索/状态筛选 | 7 个可辨识示例，状态计数、搜索空结果、排序 |
| R03 | 分类/标签入口和高亮 | Dock 独立页面 → 筛选任务；sidebar 与 chip active；分类+标签可组合 |
| R04 | 多选批量栏 | 勾选 → 数量/暂停/继续/标签/移除/取消；标签实际改变内存示例 |
| R05 | 添加/目录 picker/失败 | 空输入校验、链接校验、本地 torrent 选择；目录层级、失败不可确认、返回保留草稿 |
| R06 | 详情/Tracker/保种 | 点击任务名；四 tab；重新汇报/校验/目标设置有处理中与完成模拟；移除确认 |
| R07 | 限速/分享率/MoviePilot | 设置分区；非负数限制；应用显示模拟反馈；MoviePilot 可点失败与入口说明 |
| R08 | Dock/单手/安全区 | 四个明确主模块 + 独立添加；44px；safe-area inset；手动与系统减少透明度 |
| R09 | 滚动锁/返回/切层 | 原生 dialog 焦点约束，body 锁，history 层栈，逐层回退，桌面面板宽度调节 |
| R10 | 空/加载/失败/处理中可点 | 页底状态演练，失败重试、skeleton、添加/暂停等异步模拟处理中反馈 |
| R11 | 示例与真实边界 | 顶部全局说明、sidebar、列表脚、弹层路径、设置和项目 metadata 都标注；无 NAS 网络 |
| R12 | 真 OpenDesign 与 PNG | 项目 exact GET、文件 exact readback、artifactManifest、导出接口返回真实 PNG |

“应用目标”“全局策略”的值在本原型没有实现跨刷新持久化或生产策略引擎；显示处理反馈不等于已写入 NAS。Mock 的目的是验证操作路径与反馈，不是完整业务实现。

## OpenDesign 实际文件与预览

项目 ID：`fnos-pt-workspace-redesign`

Windows 项目实际目录：
```
%APPDATA%\Open Design\namespaces\release-stable-win\data\projects\fnos-pt-workspace-redesign
```
其中 `desktop.html` 与 `mobile.html` 均是真实注册的 HTML artifact。项目 metadata、resolvedDir、文件 manifest 可见 `project.json`、`registered-files.json`。`registration.json` 是初次创建记录；最终内容以 exact-readback 后的 HTML 与 registered-files 为准。

WSL 交付目录：
`docs/design/qbpanel-inspired/`

推荐评审截图（标准视口、没有长图拼接重复）：
- [桌面 1440×1024](../design/qbpanel-inspired/desktop-viewport.png)
- [手机 390×844](../design/qbpanel-inspired/mobile-viewport.png)
- [窄手机 360×780](../design/qbpanel-inspired/narrow-viewport.png)
- [桌面 Tracker](../design/qbpanel-inspired/desktop-tracker.png)
- [手机 Tracker](../design/qbpanel-inspired/mobile-tracker.png)
- [桌面目录失败](../design/qbpanel-inspired/desktop-directory-error.png)
- [手机目录失败](../design/qbpanel-inspired/mobile-directory-error.png)
- [桌面设置](../design/qbpanel-inspired/desktop-settings.png)
- [手机设置](../design/qbpanel-inspired/mobile-settings.png)

OpenDesign 原生导出：`desktop.png`、`mobile.png`。注意 0.25.0 的导出在本次生成的是长图/分段捕获，固定 sidebar 与 Dock 出现重复捕获、滚动条痕迹；**不能把该导出当无瑕疵的视口图**。标准 viewport 图由 Playwright 读取 OpenDesign exact artifact 后渲染并截取，来源在验证文件明确记录，没有冒称为原生导出。运行时 DOM 验证只有一个 Dock 和一个 sidebar brand。

直接交互：在 OpenDesign 中打开上述项目的 HTML artifact；也可本地浏览器直接打开交付目录里的 `desktop.html` / `mobile.html`。两者均自包含，不需要真实下载器。

## 验证结果与未闭环项

执行：`node docs/design/qbpanel-inspired/verify.cjs`

最终真实输出：**45 passed / 3 viewport configurations**（1440×1024、390×844、360×780），详见 `verification.json`。

覆盖：横向不溢出、单 Dock/brand、搜索空态、状态筛选、分类/标签、批量标签、详情 Tracker、保种入口、面板宽度、添加校验、目录失败 disabled、嵌套返回保留草稿与锁、设置反馈、MoviePilot 失败、透明度关闭、加载/空/失败恢复、末任务可完整滚至 Dock 上方、添加示例处理反馈、触控尺寸。无浏览器 JS 错误，无外部业务请求。

实际视觉检查发现并处理：异常任务改“查看错误”而非无意义的暂停；手机容量明确“总大小”，做种任务明确“下载完成·做种中”。

未完成/限制：
1. 真机 iOS/Android、飞牛 App 内嵌 WebView、软键盘和辅助技术读屏尚未实测；不等于生产移动端验收。
2. Dock 是覆盖式浮动层，视口中间卡片可能在滚动经过它时被短暂遮住；页面已有底部留白，并测试末项能完整滚出。若最终选择绝不覆盖内容，需要后续设计评审决定改为固定占位底栏，而不是默默声称已无遮挡。
3. OpenDesign 原生长图导出固定元素重复捕获属于当前实际限制，保留原始证据并提供正常视口截图替代评审。
4. 目录真实权限链路未修复，picker 故意没有“选择成功”的假流程。
5. 分享率、限速、重新汇报/校验是原型反馈，不接 API；文件只保留单示例与优先级操作，不是完整生产文件树。
6. 未做实站 PT 规则校验、真实 MoviePilot 链路或大数据性能承诺。

## 本轮评审决定（2026-10-18）

- **桌面**：侧边栏的“全部 / 下载中 / 做种 / 暂停 / 异常”是唯一状态导航；主区不再重复渲染状态 chips、tab 或状态计数导航。主区只保留当前状态视图标题与数量、搜索、排序、筛选摘要、选择/批量入口。
- **手机**：没有侧边栏，因此保留一套可见的状态筛选；不在筛选抽屉中重复状态。分类与标签不是 Dock 同级页面，而是统一“筛选”按钮打开的底部抽屉，选择后回到唯一任务列表并显示可清除的筛选摘要/高亮。
- **手机 Dock**：改为轻量工作区操作“筛选 / 添加 / 设置”；删除分类、标签、任务等伪主导航，不用凑导航页面。选择模式显示复选框与批量栏，并替换选择入口；未进入选择模式时不显示默认 checkbox，批量栏与底部操作栏不重复承担同一入口。
- 本次仅更新真实 OpenDesign artifact 与设计文档，不改 `src/`、`gateway/`、`native/`，不打包、不提交、不推送、不访问 NAS。

### 本轮验收重点

- 桌面点击侧栏状态后，主列表标题、数量与侧栏选中态同步更新；主内容没有重复状态导航。
- 手机状态筛选只出现一套；Dock 不出现状态/分类/标签导航。打开“筛选”后可选择分类/标签，关闭抽屉回到同一列表，筛选摘要可清除。
- 普通浏览不显示任务 checkbox；点击“选择任务”进入选择模式后才显示，批量操作栏与选择模式互斥。
- PNG 预览通过 OpenDesign daemon `POST /api/projects/{id}/export/image` 生成原生导出；`desktop-viewport.png` / `mobile-viewport.png` 通过 Playwright 使用 exact read-back HTML、`fullPage:false` 截取标准视口，二者渠道在验证记录中明确区分。

- `workspace.html`：原创设计源；`desktop.html` / `mobile.html`：真实注册内容的本地副本。
- `register.py`：仅首次创建项目，非幂等，不要重复创建同 ID；`sync.py`：显式 overwrite 更新现有 artifact 并 exact readback 与原生导出。
- `verify.cjs`：浏览器交互/断言/viewport 截图；使用本机 `/usr/bin/google-chrome`，不依赖新下载浏览器。初次默认 headless shell 缺失，安装下载超时，已换可用 Chrome 完成实测。
- `project.json` / `registration.json` / `registered-files.json` / `verification.json`：取证与验收记录。

全部文件仅设计用途。没有产品实现或发布授权。

## 追加评审：独立分析页面（取代前文旧 Dock 架构）

以下为最新设计决定，覆盖前文 R03/R08 与旧“任务/分类/标签”Dock 描述，其余历史记录保留。

### A01 导航与返回契约

- 手机 Dock 固定为 **筛选 / 分析 / 设置**；添加是独立 FAB，仅任务页出现。分析不是分类筛选抽屉，而是独立页面，分析页有可见的“返回任务工作区”。分析/设置不显示 FAB，选择/弹层仍独占底部操作区。
- 桌面仅侧栏增加分析入口；原有侧栏仍是唯一状态导航，不在主区或分析页复制状态 chips。
- 页面切换保留 `status, q, category, tag, station, sort` 和每个页面自己的滚动位置；返回任务按钮不清理筛选。切换清除选择模式、选中任务和详情，避免隐藏批量操作。分析进入时不受任务筛选影响。
- 点站点返回唯一任务页：保留状态/搜索/分类/标签，新增或替换单个 station 条件，以 AND 组合，不隐式带入分析的完成/运行口径；从列表顶部展示结果。摘要可单独清除 station，清除全部则重置状态、搜索、分类、标签、station；无匹配显示空态和清除入口。
- 切去设置后仍可经 Dock 分析或筛选返回任务；筛选从分析进入时先恢复任务再打开原有抽屉。

### A02 存储需求与未来数据契约（不是已实现 API）

`StorageSnapshot = {snapshotId, observedAt, source, partial, volumes[], totals, errors[]}`。
每个卷建议字段：`volumeId`（服务端归一后的可信、稳定身份）、`identityConfidence`、`mountGeneration`、`authorizedRootIds[]`、`displayName`、`status`（ready/offline/permission_denied/unavailable）、`totalBytes`、`freeBytes`、`availableBytes`、`observedAt`。容量以整数字节传输，UI 转换 IEC 单位；示例页面使用 TiB。

- **唯一身份而非目录名去重**：授权下载目录解析到文件系统卷/挂载容量域，相同卷上的多个目录与 bind mount 只占一张卡；使用平台稳定卷 ID/文件系统 ID 和挂载关系归一，不以显示名、路径字符串或孤立设备号永久标识。挂载重新关联须重新验证；身份无法建立则标记未知并排除总合计。
- 这里的“硬盘”展示对象是文件系统卷，不保证等于物理盘（RAID/LVM/共享池/网络挂载均可能不同）。同池多个子卷若共享容量不能重复累加，需服务端 `capacityDomainId` 归一；未确认不累加。授权多个目录指向同卷只读一次容量，不按路径求和。
- `usedBytes = totalBytes − freeBytes`；**不能**用 `totalBytes − availableBytes` 冒充已用。`freeBytes` 是文件系统全部空闲，`availableBytes` 是当前应用身份可用；`free − available` 为保留/身份不可用空间，不属于已用。展示重点为总容量和已用，次要显示 free、available、保留说明。
- 聚合只计 ready 且唯一容量域，显示“可取得卷合计 / 已取得数 / 总数”；离线、权限不足、容量不可取得显示未知而非 0，错误不参与求和。旧快照须带过期标记，不能把最后已知值冒充当前值。
- 后续必须由**服务端 statfs 或平台可信卷 API**在应用授权范围内提供：例如 statfs 的 `f_blocks × f_frsize`、`f_bfree × f_frsize`、`f_bavail × f_frsize`，并验证边界/溢出和平台权限。qB 的路径剩余空间/当前目录 free 数据不等于全部卷总/已用能力，原型不声称 qB 已有完整容量 API。
- 只解析已授权根所属卷；不得枚举全盘、不递归扫描、不通过符号链接逃逸授权。不向前端返回未授权卷或真实敏感根；权限撤销、离线重挂载、超时要显式返回安全 reason code。
- 示例容量域 A 含电影/剧集两个目录，B 含一个目录，另有离线 C、权限不足 D、不可取得 E。所有身份、路径与容量均为设计 fixture，没有实际 statfs 调用。

### A03 保种口径、归属和数据契约

建议 `SeedSnapshot = {snapshotId, observedAt, complete, mappingVersion, scope, sites[], uniqueTotal, excluded, errors[]}`；每站 `{siteId, safeDisplayName, taskCount, logicalSizeBytes, hashes}`（hash 集合可仅留服务端）。使用同一完整任务快照和有界 Tracker 映射结果；不对分页半截快照标注完整总计。`size` 对应任务逻辑总大小/total_size 字节，不用已下载量或上传量，不代表独占物理占用、硬链接去重后空间或卷已用量。

| 任务状态（均须 private、完成、文件可用） | 可保种已完成任务（默认） | 当前运行做种 |
|---|---|---|
| uploading / stalledUP（包括零速等待连接） | 计入 | 计入 |
| forcedUP | 计入 | 计入 |
| stoppedUP / pausedUP | 计入 | 不计 |
| queuedUP | 计入 | 不计 |
| 未完成 downloading / stalledDL / forcedDL / stoppedDL / queuedDL / 尚未下载 | 不计 | 不计 |
| missingFiles / error / checkingUP / checkingDL / moving / 未知状态 | 不计，列入排除/待确认 | 不计 |

“完成”不是只看显示百分比：未来服务端以任务完成字段、剩余量和状态一致性校验；文件可用是可信快照结论，不为分析页逐文件全盘读取。stopped/paused 的已完成任务与未下载暂停任务必须区分。已完成但存储离线或文件缺失不称可保种。private 字段缺失为待确认，不从 PT tag 推断。

- private 任务站点取自 Tracker **host 域名**标准化后与版本化人工站点映射；先解析 URI 再只保留域名，忽略用户信息、路径、fragment、query，不将 passkey 或完整 URL 返回前端/截图/日志。不用标签猜站点；同站不同域名通过明确映射归并，不盲目按 eTLD+1 合站。
- 同站多个 Tracker 以 `(siteId, torrentHash)` 去重；一个任务可归属多个站，站点行之和不能作为全局总计；全局按 hash 去重一次后求数量与逻辑大小。
- 无映射 private 任务归“未知站点”。部分 Tracker 已映射、部分未映射时保留 unknown 归属并记录映射不完整，不默默丢弃；公开任务不计入 PT 站统计。映射尚未获取和确认无映射分别标记，不把加载中当未知的最终结果。
- 页内切换默认/运行口径、逻辑体积降序/数量降序/名称排序；所有口径为全任务快照范围，不受任务页已有筛选影响。点击行仅增加站点筛选，不带入统计口径，规则见 A01。
- 演示数据：一个已完成暂停 private 任务归未知，一个 forcedUP private 任务同时归港湾/林间且重复港湾 Tracker 去重；公开做种、未完成暂停和缺失文件均不计。任务数字/体积通过 fixture 汇总而非访问真实 PT。

### A04 状态与线框

```
手机                              桌面
存储与保种分析  ↻                  侧栏：唯一任务状态 / 分析
← 返回任务工作区                    主区：← 返回任务工作区
示例时间 · 刷新                     示例时间 · 刷新
授权卷合计（可取得 / 总数）           授权卷合计
[卷 A 已用 / 总容量]                 [卷 A 已用 / 总容量] [卷 B 已用 / 总容量]
[free / available / 保留说明]         [离线 C]             [权限 D]
[卷 B] [离线 / 权限 / 不可取得]        [不可取得 E]
PT 站：口径 ▼ / 排序 ▼               PT 站：口径 ▼ / 排序 ▼
站点 → 任务数 / 逻辑大小              站点 → 任务数 / 逻辑大小
hash 去重合计 / 统计说明              hash 去重合计 / 统计说明
[筛选 | 分析 | 设置]  无添加 FAB       原有桌面操作入口，不复制任务状态
```

- 分析有独立 loading skeleton、error + 重试、empty、ready 和示例刷新时刻；单卷异常不阻塞其他卷。分析页底有可点的状态演练；不伪造成功读取 NAS。
- 手机单列、长身份/路径换行；44px 点击区、底部与顶部安全区、末项可滚到 Dock 上方。保留原型覆盖式 Dock 的已知取舍，真机/WebView 仍未验收。

### A05 真实 OpenDesign 与证据

- 同一真实项目 `fnos-pt-workspace-redesign` 更新 `desktop.html`、`mobile.html`，新增注册 artifact `desktop-analysis.html`、`mobile-analysis.html`；四份均 exact GET readback 比对。
- 原生导出：[桌面分析 PNG](../design/qbpanel-inspired/desktop-analysis.png)、[手机分析 PNG](../design/qbpanel-inspired/mobile-analysis.png)。原生长图仍有固定/粘性控件重复捕获，保留原始证据，不称干净视口图。
- 精确读回 HTML 的浏览器视口图：[桌面分析](../design/qbpanel-inspired/desktop-analysis-viewport.png)、[手机分析](../design/qbpanel-inspired/mobile-analysis-viewport.png)、[360px 分析](../design/qbpanel-inspired/narrow-analysis-viewport.png)。这三张是 Playwright 截图，不是 OpenDesign 原生导出。
- `sync.py` 支持既有文件更新与分析 artifact 首次注册；`verify.cjs` 新增 Dock 三项、独立分析、隐藏 FAB、返回筛选/滚动保持、hash 去重、口径切换、站点返回筛选、状态演练、刷新、44px 与无横溢出断言。最终结果见 `verification.json`，先前 45 项属于历史轮次。
- 最终执行 `python3 docs/design/qbpanel-inspired/sync.py && node docs/design/qbpanel-inspired/verify.cjs`：四份 artifact 注册/更新、逐字节读回、原生 PNG 导出完成；**48 passed / 3 viewport configurations**（1440×1024、390×844、360×780），无 JS 错误和外部业务请求。分析末尾可滚至 Dock 上方，Dock 底边在视口内；safe-area 为 CSS 设计验证，不冒充真机安全区验收。
- 只改设计 HTML/脚本/文档/证据，不改产品实现、不打 FPK、不访问真实 NAS 或 PT 链接。

## 最新用户决定：主页顶部单套状态导航（覆盖旧侧栏唯一导航决定）

- 下载任务主页最上方常驻一套「全部 / 下载中 / 做种中 / 暂停中 / 异常」状态按钮；桌面一行、手机局部横向滚动，触控目标至少 44px。选中项强对比高亮并有 aria-pressed；侧栏不重复状态，筛选抽屉也不重复状态。分析等独立页面不渲染任务状态导航。
- 状态根据 qB state 判定，不把所有 progress=1 任务误称做种中：下载中包括 downloading/stalledDL/forcedDL/queuedDL/metaDL/forcedMetaDL，做种中包括 uploading/stalledUP/forcedUP/queuedUP；暂停中包括 stoppedDL/stoppedUP 及旧 pausedDL/pausedUP；异常包括 error/missingFiles。校验/移动/未知仍可从全部看到。
- 「全部」只清状态，保留搜索、分类/标签和站点；说明文字明确此行为。「清除所有筛选」独立重置状态、搜索、分类/标签、站点和资源上下文。移除最后条件立即恢复快照中的任务，无需手动刷新。
- 分类/标签/站点摘要和状态同步，任何筛选上下文变更清理选择集合；刷新只更新完整快照，过期请求不得覆盖较新结果。本轮允许产品 UI 与回归测试实现，不授权打包、Git 操作或 NAS 部署。
