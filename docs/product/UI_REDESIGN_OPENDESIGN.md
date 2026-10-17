# 飞牛 PT 下载 · UI 重设计基线（native 1.2.4）

## 授权、审计与设计依据
本轮已授权设计、实现与隔离验证，不访问 NAS、真实任务或用户凭据，不执行 Git 操作。基线为正式不可变 native1.2.3 的 UI、manifest 与 `app/ui/config`。审计读取 `PRODUCT_DESIGN.md`、`NATIVE_SCOPE.md`、`pt-priority.md` 及当前源码；旧设计中 Docker、账号入口和 6881 默认值不再是当前 native 的规范，认证以 1.2.3 实现为准。本轮不改 gateway/native 或 qB 操作语义。

项目未提供 OpenDesign CLI、MCP、组件规范或设计文件，当前工具目录也没有可调用的 OpenDesign 工具。**采用 OpenDesign 式开放、可审查、以任务为中心的设计原则，不声称调用了 OpenDesign 产品或生成工具。**原创矢量图标由本项目编写，PNG 从该 SVG 真实渲染，不使用 qB 官方图形。

### 现状与差异
- 保留：唯一 fnOS gateway 主入口、qB5.2.4、添加结果/异步 bdecode 诊断、PT 开始/强制开始/暂停、端口、全局/时段限速、脱敏信息、认证边界。
- 重构：稀疏侧栏、手机操作按钮密集、完成比例与 PT 数据同级、长设置缺乏分组、按钮浏览器点击高亮、加载状态缺少 aria-busy。
- 不新增批量写入 API；当前产品没有批量选择。单任务卡明确划分信息/操作，所有写动作等待中禁止重复，删除独立危险区且保留确认。这比伪装一个不完整的批量功能更安全。
- 更名：显示名称统一为“飞牛 PT 下载”。内部 app ID `fnos-qbittorrent-native`、gatewayPrefix、数据目录、升级标识不变。

## 设计基线
手机优先，桌面扩展。背景冷灰、主色深靛蓝、成功青绿、错误红；正文高对比，状态不只靠颜色；44px 最小触控目标，8px 节奏，16/24px 圆角。使用系统中文字体，无远程字体或统计。任务名是主标题，状态与完成度次之，上传/分享率/保种时间为 PT 辅助信息。速度为独立数据区，动作不覆盖整卡，不点击卡片空白触发 mutation。

应用图标：靛蓝圆角方形，白色下载箭头、底部托盘、青绿叶片/种子，轮廓在深浅背景均可辨。源 `public/app-icon.svg`；入口 64/256px PNG、包根 ICON.PNG/ICON_256.PNG；网页 SVG favicon 和品牌图片共用同源资源。

## 信息架构与线框
### 桌面（验收默认 1440×900；用户消息桌面尺寸含不可解析占位符，未擅自推定其值）
```
[品牌 / PT 工作区] | [任务总览                      设置]
[全部任务          ] | [任务数 | 下载中 | 已完成/保种]
[下载中            ] | [添加任务] [搜索____________] [筛选]
[已完成            ] | [名称/状态/进度 | 大小 | ↓↑ | 操作]
[已暂停            ] | [PT 累计数据                | 开始 强制 暂停]
                      [详情                            删除]
```
顶部设置是唯一设置入口；侧栏筛选只是读取本地列表。无任务与无搜索结果区分。详情为居中浮层，内部滚动；关闭保持在右上方。
### 手机 390×844
```
[飞牛 PT 下载                 设置]
[任务总览 / PT 保种工作区]
[全部 | 下载中 | 已完成]
[添加任务] [搜索____________]
[筛选______________________]
[任务名 / 状态 / 完成进度]
[大小             ↓下载 ↑上传]
[累计上传 / 分享率 / 做种时间]
[开始] [强制开始] [暂停]
[详情]                    [删除]
```
手机不缩小桌面表格，侧栏收为顶部品牌/导航，工具条换行，卡片动作完整分行。浮层留安全区与遮罩外沿，长内容滚动时右上角关闭可见。未引入底部导航以免与 iframe 手机宿主导航重叠；顶部导航满足明确导航需求。

## 状态模型
- 列表：连接中 → 已载入/空态/无匹配；失败显示固定错误区并保留上次列表。
- mutation：idle → busy（disabled + aria-busy，文案/状态可见）→ verified success / explicit error / unknown。finally 清 busy；没有延迟 active class、没有业务自动重试。CSS active 只在实际按压且非 disabled 时存在，不做 transform/box-shadow 延迟过渡；保留键盘 focus-visible。
- 添加：默认路径加载/失败可手填 → 校验 → 提交 → 已接受但待观察 → 新 hash 确认 / bdecode:4 时窗关联未确认 / 未知。45秒观察是实际后台状态，不是点击残影，允许关闭后继续观察，重开保留结果。
- 设置：加载 → 编辑 → 保存 → 读回核验；普通/高级分组保留实际字段与单位。不能把保存时段等同触发。
- 详情：加载/局部失败保留旧数据 → 状态/Tracker/文件；私有种子禁用发现机制不是错误。遮罩点击仅 target===currentTarget 才关闭，内点击不关闭。

## 需求追踪与验收
| ID | confirmed 主路径 | 实现/验收契约 |
|---|---|---|
| UI-R01 | 任务总览 | 桌面/手机正式 iframe，筛选/搜索、卡片层级、无横向溢出 |
| UI-R02 | 添加任务 | URL/file/magnet，实际新 hash；合法文件与受控失败，不自动重放 |
| UI-R03 | 保种操作 | 开始清 force、强制开始、暂停，实际状态与 force 回读；不改分享限制 |
| UI-R04 | 详情诊断 | 元数据/Tracker脱敏/累计PT数据/文件；加载与局部失败可见 |
| UI-R05 | 端口设置 | 1–65535 校验，固定端口保存读回，不修改发现/管理端口 |
| UI-R06 | 全局/时段限速 | KiB/s，0不限速，日期/本地时区说明、保存读回；真实触发单列 |
| UI-R07 | 错误反馈 | 红色可读错误、bdecode:4响应未知/关联未确认、不泄漏 URL、无自动重发 |
| UI-R08 | 浮窗 | 设置/详情/添加右上关闭、长内容可滚动、内点击保留、外点关闭 |
| UI-R09 | 移动触控 | tap highlight透明、touch-action、请求结束 busy 清除，禁止等待中双击 |
| UI-R10 | 名称/图标 | 显示名统一，SVG/PNG资源尺寸/引用校验，内部ID不变 |

## 最终验证结果（交付 native1.2.5）

1.2.4 首次构建保留不可变，但浏览器验证发现新增 SVG 放在根路径会被现有 gateway 静态资源白名单拒绝。没有扩大白名单/认证边界；改用已有 `/assets/` 静态通道，构建下一个不可变 **1.2.5**。1.2.4 是失败候选，禁止推荐安装。最终图标源 `public/assets/app-icon.svg`（`public/app-icon.svg` 保留相同原始设计）；1.2.5 品牌、favicon、入口 PNG 都已校验。

- `python tools/build_native_1_2_5.py`：TypeScript/Vite + fnpack 成功。包内所有非 UI/入口品牌文件与1.2.3逐字节一致，gateway/native 源码与审计前 SHA 一致。
- `GO111MODULE=off go test -count=1 ./gateway ./native`：两包通过，输出 `evidence/native125-go.txt`；2条触控/aria-busy静态回归通过，初始 RED 证据 `evidence/ui124-red.txt`，最终 GREEN `evidence/ui125-contract.txt`。
- `python tools/verify_regression125.py`：最终包真实 qB API v5.2.4 / Unix gateway / iframe，桌面1440×900、手机390×844通过；详情/设置内部点击不关闭，遮罩外点关闭，长设置关闭常驻；真实端口分别49243/49244读回；正常/备用限速、时段字段读写、非法限速零写入、普通设置保留分享限制；保种强制/暂停/普通开始及force标志回读通过。证据 `evidence/pt125-browser.json`。
- 真实私有种子双进程传输4194304字节、文件校验一致；真实时段0→1→0触发与速率读回、重启持久化通过；跨午夜真实触发未验证。证据 `evidence/pt125-real.json`。
- 添加合法URL/file/magnet各新增1 hash，HTML/JSON各0 hash且bdecode:4红色错误、响应未知/关联未确认、重开/刷新保持；5次用户提交仅5次POST。添加观察中aria-busy=true，结束为false且按钮重新启用，透明tap highlight、touch-action与0s transition在真实DOM中验证；加载/错误截图来自最终包。证据 `evidence/diagnostics125-browser.json`、`evidence/native125-real-regression.txt`。
- 最终包截图12张：`evidence/ui125-{overview,detail,settings}-{1440,390}.png`、`evidence/ui125-add-{loading,html,json,url,file,magnet}.png`。手机概览截图已视觉检查，无明显横向溢出/遮挡/动作拥挤；DOM也验证无横向溢出。
- 入口名称/内部ID/prefix及4个PNG尺寸/哈希：`evidence/native-package-audit-1.2.5.json`。网页品牌图片实际加载成功。未在NAS桌面/手机原生入口安装，因此不能声称平台实际显示已验收。
- 交付 `release/fnos-qbittorrent-native-1.2.5-x86_64.fpk`；SHA256 `14b04dfc42ba2396bbab8a64b4abea770fc055a3688ff7191403253b980c5bce`。

未完成：真实NAS升级/安装/ACL、物理手机WebView点击残影确认；用户桌面尺寸占位符未解析，采用1440×900明确默认。没有新增批量选择/批量mutation（保留原有单任务操作与确认删除）。当前按钮不存在延迟active状态；45秒添加观察仍为业务loading，不人为提前清掉约束。原有许可证/对应源交付限制沿用，不据本轮UI测试扩大分发声明。

## 验证与限制
最终验收结果与证据追加于下方，未执行不标通过。所有截图与实时数据必须来自最终交付 1.2.5 包；旧 1.2.3 证据只作审计输入。真实 NAS 安装/升级、fnOS 手机 App 原生 WebView/物理触屏残影、平台入口实际展示仍需用户真机验证。WSL Chrome 触屏模拟不等于真机。未改变认证边界；本地统一网关模拟器仅用于隔离测试，绝不入包。


## MoviePilot / labels implementation addendum

原始 native 1.2.5 UI 基线已从不可变 source overlay 恢复；1.2.9 覆盖内容保存在 evidence/UI_REDESIGN_1.2.9-overwritten-baseline.md，仅供审计，不表示已验收。后续连接器与分类标签增量契约见 MOVIEPILOT_CONNECTOR_OPENDESIGN.md、MOVIEPILOT_INTEGRATION_OPENDESIGN.md。最新用户实施授权优先于设计阶段的禁止源码改动限制。逗号标签不可单个保留时拒绝，不做 NFC；不承诺分类 rename；路径/autoTMM 操作需确认移动风险。
