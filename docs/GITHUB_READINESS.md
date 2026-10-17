# GitHub readiness / 可恢复清理报告

## 结论

**源码整理已完成，尚不可宣称公开发行就绪。** 无 `.git`，未执行 git init/commit/push、创建仓库或访问 NAS；无新 FPK。原创代码现已明确为 GPL-3.0-or-later（Copyright (C) 2026 alvin-7）；第三方许可证独立。完整干净构建入口和开发依赖安全仍是公开发行门槛。用户仍需决定目标仓库/可见性；不需要提供 NAS 密码或 PT URL。

## 清理清单与恢复

- [x] 原始 221 个源码/工具/文档/依赖文件已备份到私有 `.runtime/github-readiness-backup/originals/`，附 `original-manifest.json` 的 SHA256。
- [x] 更新 README、THIRD_PARTY_NOTICES、.gitignore；新建 LICENSE pending、SECURITY、.gitattributes、SOURCE_DELIVERY、工具/逻辑 archive 索引、只读上传扫描器。
- [x] 仅三个已有工具改动：`verify_all.sh` 去个人 Node PATH；`verify_regression140.py` 修正文档版本；`verify_connector140_real.py` 相对解析项目根，删除默认私网主机，强制显式测试 bind。最后一项是测试工具行为变化：未提供 bind 在创建 fixture 前失败；已实际验证有/无 bind 分支。
- [x] 清理阶段 `src/`、`gateway/`、`native/`、package.json/lock 随后按授权更新 license 与已审计 dev 依赖；native 与历史 FPK 未改。
- [x] 所有历史 FPK/源码包、用户数据、旧工具及 staging 均保留；不 rm 大目录。旧路径存在文本复用依赖，因此 archive 采用明确索引，不物理搬迁。
- [x] 重跑前备份旧 140 evidence 到私有 `evidence-originals/`。新结果仍在忽略的 evidence/runtime 中。不要把重跑证据误当原始冻结证据。

恢复时只恢复以上明确修改的已有路径，并逐项移除新增文件；不要批量覆盖可能存在的并发改动。备份本身可能含旧凭据，严禁上传。

## 上传范围

精确候选文件列表见 [GITHUB_UPLOAD_FILES.txt](GITHUB_UPLOAD_FILES.txt)。该列表由 `tools/readiness_scan.py` 从当前 `.gitignore` 计算；扫描不会初始化 Git，也不会读取被忽略的大目录。机器报告保存在私有 `.runtime/github-readiness-backup/candidate-scan.json`，包含候选路径/大小/hash及仅位置类别的警告。

上传：原创 src/gateway/native、测试/安全 fixtures、审阅后的工具、公开资源、锁文件、配置及筛选后文档。目录名允许不代表目录内每个文件允许。忽略规则是本次上传边界，不是永久删除许可。

排除：整个 `.runtime`、`node_modules`、`dist`、`webui`、`evidence`、`release`、test-results/playwright-report/cache；FPK/tar/zip/log/socket/env/凭据文件；native-package 与旧 Docker staging；fnpack 二进制；现场调查/历史发行/平台采集文档；含环境默认主机的旧 connector130/132/135 Python 入口。原文件仍本地保留；完整排除项以 .gitignore 为准。

扫描器只实现此文件的简单 ignore 规则，不是通用 Git 库。将来有 Git 后必须复核**实际暂存清单**，包括已跟踪或强制添加的忽略文件；不能用本报告证明未来任意上传安全。

## 源码安全与重复审计

- 在候选集中未发现私钥/常见 provider token 格式、个人绝对 home 路径或超过 5 MiB 文件；无 symlink 候选。启发式扫描不是穷尽秘密证明。
- PT/signature URL 警告位于 gateway diagnostics 测试、tests/business/magnet fixtures 及历史 tools browser fixtures：已检查为合成/脱敏 canary、保留域或动态隔离服务地址；只记录类别/位置，不公开值。
- credential-literal 警告在 `gateway/connector*_test.go` 和 `tools/test_connector134_validation.mjs`，是隔离测试密码/错误密码，不是 NAS 密码。实际 qB 临时凭据仅 runtime 文件生成，connector140 使用随机密码。
- 私网地址警告剩余于 `tools/test_connector132.mjs`、`verify_server_domains.py`、`verify_gateway*.py`，是验证网络范围/Host/域名行为的静态 fixture 或固定 Docker 测试网络，不能简单改成公网文档 IP 而保留相同验证语义；不可作为现场 NAS 默认。含环境绑定默认的旧客户端入口已排除。
- `exec` 警告是本地历史 harness 读取并转换受控源码，仍增加维护风险；不读取网络代码，不在生产入口使用。未来应抽成共享 fixture 模块并测试，不做仓促重构。
- 网关审阅确认真实 Unix ConnContext + UID/admin 前置、公开 CSRF marker + 同源/拒绝预检、不向后台透传身份头、重认证前置且业务写不重放。生产 raw 后端日志可能含 URL，必须继续私密保管。
- **重要边界**：connector.go 当前是两段 API 路径语法边界和保留路由拒绝，不是最小业务 allowlist；持有 MoviePilot 密码者能访问广泛 qB 业务 API，包括任务/文件操作。不能把它宣传为只读或严格最小权限；仅受信自动化和防火墙内使用。认证不是细粒度授权。
- native lifecycle 仍用 Linux/amd64 pidfd syscall、进程 fingerprint；非 x86_64 不在支持范围。现有配置迁移/错误日志及文件权限仍需 NAS 现场审查。
- `public/app-icon.svg` 与 `public/assets/app-icon.svg` 是相同 branding 的重复路径，后者是网关允许加载路径；为避免破坏旧入口及冻结包，未删前者。
- 旧 package.json=1.0.0、旧 staging manifest=1.1.4、旧 README=1.0.8 与最终 FPK=1.4.0 混杂；README 已明确权威关系。未伪造统一版本或改不可变包。版本专用脚本重复主要来自历史冻结，不认定为可直接删除的死代码。

## 实际执行与证据

| 检查 | 真实结果 |
|---|---|
| `npm run build` | PASS，TypeScript + Vite 41 modules |
| `VITE_NATIVE=1 npm run build` | PASS，41 modules |
| `GO111MODULE=off go test -race ./gateway ./native` | PASS，两包；清理后重跑仍通过 |
| `GO111MODULE=off go vet ./gateway ./native` | PASS |
| selection140 / label batch130 / labels130 / connector134 JS contracts | 4 个入口均 PASS |
| `SELECTION_PACKAGE=140 python3 tools/verify_selection140_real.py` | PASS，最终包真实 qB 5.2.4 + Unix gateway + 1440/390 iframe；3 个 private fixture 批操作、标签分类、真实读回、注入单项失败无重放 |
| `python3 tools/verify_regression140.py` | PASS，真实 4 MiB private transfer、强制/停/普通开始、重启/定时限速真实触发；12 个 PT UI case，5 个添加诊断 case，含受控真实非法内容；不是 mock 代替 qB |
| 显式本机接口 `verify_connector140_real.py` | PASS，Docker 中 pinned qbittorrent-api==2026.6.0 登录/版本/分类/标签 CRUD/multipart add读回、恶意 origin/敏感路径拒绝、关闭监听；不是完整 MoviePilot 应用验收 |
| connector140 未提供 bind | 按预期 exit 1，前置拒绝；不视为成功集成测试 |
| artifact-only consistency | PASS，FPK/staging、src/gateway/public与冻结源码、原生 transformed dist、源码包绑定、旧1.3.9校验均通过 |
| 原 `audit_selection140.py` 完整运行 | exit 1：已有不可变 verification overlay，脚本拒绝覆盖；随后仅执行 overlay 写入前所有只读检查并通过，未删/改 overlay |
| npm production audit（官方 registry） | 0 advisories |
| npm all-dependencies audit（官方 registry，升级前） | 3 high：@playwright/test、playwright、vite；已按审计范围选择兼容修复路线升级至 @playwright/test/playwright 1.55.1、vite 7.3.7，升级后 audit 为 0 vulnerabilities。lock 已更新并完成 npm ci/build 回归 |

首次默认 npm mirror 不支持 advisory endpoint，已改用官方 registry 获得真实结果，未把失败当通过。详细测试日志只保存在私有 backup；报告不复制地址或凭据。清理阶段仅改文档及 harness，后续五项修复改变当前源码；两阶段均未生成新 FPK。包 runtime/source 匹配检查属于旧冻结版本，不证明修复后的源码已打包；这些改动在旧包冻结之后。

### 当前源码：五项定点修复与新证据

- connector 使用独立有界请求互斥；全局配置/会话锁不跨网络 body、PBKDF2 或 backend 转发。管理 status/disable 可在这些操作挂起时完成。慢登录计算后及 body 读取后复核配置 generation/会话，阻止禁用/换密后迟到请求继续认证或转发；已转发的业务不重放，也不声称可撤销已送达后台的操作。
- reveal 在锁内取得密文及密钥一致快照，锁外解密；并发 configure/reveal race 回归通过。
- batch 与单任务共用 state+force 谓词；`stoppedUP + force=true` 必须等待真正非暂停状态。
- 搜索、状态筛选、资源上下文变化清空选择/编辑器；刷新剔除已删除 hash；批量开始时复制去重并限定当前可见目标。
- 已保存密码隐藏立即清明文、取消计时器；卸载/离开高级设置清理 timer，generation 阻止迟到 reveal 回填。默认仍掩码、30 秒自动清除。
- 未恢复 CIDR 或业务 allowlist。README 已更正过时严格模式文案。原创授权现已按用户确认落实为 GPL-3.0-or-later、alvin-7；历史包保留，第三方义务独立。

RED 证据在忽略的 `.runtime/five-fixes/`：Go 两个阻塞用例失败且 reveal 检出 DATA RACE；batch stoppedUP 断言失败；浏览器搜索选择残留、隐藏密码明文残留失败。首次 Vite dev server 退出导致的连接失败未算作有效 RED，改用实际编译静态 UI 后获得上述行为失败。

GREEN：`npm run build` 和 `VITE_NATIVE=1 npm run build` 均通过（41 modules）；`GO111MODULE=off go test -race ./gateway ./native`、`go vet` 两包通过；6 个 JS 入口（selection140、label_batch130、labels130、connector134_validation、pt119、five_fixes）通过。新增 Playwright 两个用例通过：搜索/筛选/资源/刷新选择生命周期，以及 reveal→隐藏→离开/重开设置。

`SELECTION_PACKAGE=140 python3 tools/verify_five_fixes_real.py` 通过：从当前源码编译 UI/Unix gateway，复用历史 pinned qB 5.2.4 runtime，仅创建三个隔离 private fixture；1440/390 真实 iframe 的强制/暂停/普通开始、分类/标签读回、资源返回、布局及单项注入失败无重放通过。结果在 `.runtime/five-fixes/selection-current-browser.json`、`selection-current-readback.json`、`real-final.log`。这是**当前源码本地验证，不是新 FPK/最终包验证**；NAS、完整 MoviePilot、真实路径映射未验收。Node 测试存在已知 DEP0205 警告，不当作零警告。

重新扫描当前候选集：216 个文件、0 symlink、无私钥/provider token/个人 home/超大文件命中；新增两个 review flag 分别为合成并发测试密码，以及仅执行本地受控历史 fixture 的 exec（未读取网络代码）。最终机器清单保存在 `.runtime/five-fixes/candidate-scan.json`；候选路径清单与扫描逐项一致，不等于将来强制暂存文件的安全证明。

新增：`gateway/connector_concurrency_test.go`、`tests/five-fixes.spec.ts`、`tools/test_five_fixes.mjs`、`tools/verify_five_fixes_real.py`。更新：connector、pt/batch、main、MoviePilot，以及 selection JS loader（解析新增共享谓词依赖）、README、本报告和候选清单。旧 FPK/源码包均不改。

## 剩余门槛与最少用户决策

1. **原创 LICENSE 已落实**：GPL-3.0-or-later、Copyright (C) 2026 alvin-7，根 LICENSE 完整 GPLv3 正文；不重授权第三方。
2. **目标仓库**：owner/name、初始 public/private、私密漏洞报告渠道。当前没有授权创建/初始化/提交/推送。
3. 开发依赖 advisories 已清零；空 checkout 完整原生 FPK 构建不完整、完整对应源码法律充分性审查仍须处理后才能公开发行二进制。Git 忽略大源码包不等于免交付源码。
4. NAS 安装/升级/socket ACL/卸载保数据、物理手机 WebView、完整 MoviePilot 应用与真实路径映射未做；当前无 NAS 操作，不能声称安装就绪。
5. 独立 reviewer 应检查这份文档与工具差异；本实现者不把自己的清理审阅等同独立批准。

## 用户确认授权与 dev 依赖 / clean-room 复核

- 工具确认当前年份 2026。根 LICENSE 已替换为完整 GPLv3 正文并附原创范围授予 GPL-3.0-or-later、Copyright (C) 2026 alvin-7；README、THIRD_PARTY_NOTICES、SOURCE_DELIVERY、package license 统一。不改第三方版权、不重授权依赖、不回写历史包。
- 精确 audit 原报告：Playwright GHSA-7mvr-c777-76hp 的受影响范围 <1.55.1，因此选 1.55.1 而非 audit 建议最新 1.64.1。Vite high 范围覆盖 <=7.3.4；试验 7.3.5 后出现 esbuild 0.27.7 的 low GHSA-g7r4-m6w7-qqqr，最终选 Vite 7.3.7 并非 force 更新兼容的 esbuild 0.28.2。未盲目 npm audit fix --force。浏览器工具直接 import playwright，因此显式锁定与 @playwright/test 同为 1.55.1。
- 最终官方 registry audit：all 0（info/low/moderate/high/critical 全 0）；production 0；独立 clean tree audit 0。package-lock 已同步。npm ci 有 esbuild install-script 审批提示；Playwright 存在 Node DEP0205，不声称零警告。
- 实跑通用及 native-mode build（41 modules）、Go race/vet 两包、六个 JS 入口均通过。先启动 loopback 静态 UI 并 curl readiness，再跑五项修复的两条 Playwright，2 passed；不是 ECONNREFUSED 冒充测试。
- `verify_five_fixes_real.py` 最终 PASS：当前源码 UI/gateway + pinned qB 5.2.4，1440/390 iframe、三个 private fixture、批量 force/stop/start、分类标签真实读回、注入单项失败不重放。中途发现移除 direct playwright 导致 ERR_MODULE_NOT_FOUND，已恢复同版本 direct 依赖并重跑成功；失败日志保留。
- 从原 216 个上传候选扩展到 **219 个**（新增 build_checkout.py、fetch_native_inputs.py、NATIVE_INPUTS.lock.json）。最终独立目录仅复制上传清单，不含 node_modules/dist/release/evidence/runtime，实际 npm ci/native UI build/Go 两个可执行文件 compile/race/vet/六 JS 全 PASS。没有读取历史 FPK。报告 `.runtime/five-fixes/clean-checkout-final.log`、`clean-audit-final.json`。
- `fetch_native_inputs.py --verify-only` 对三份缓存 qB/libtorrent/Boost 上游源码 SHA256 全通过；新脚本可按 URL 下载并 fail-closed 校验。锁记录大小、许可、Alpine recipe commit/选定 APK hash，不把部分锁说成完整运行时闭包。未为验证重新下载大型第三方归档。
- **完整 native FPK clean build = blocked**：精确完整 compiler/dev APK/Qt 私有 ABI bootstrap、运行时所有权/TLS/CA 装配、完整匹配源码法律审查及 fnpack 可信获取/hash 锁尚未闭合。未生成新 FPK；旧 FPK/历史源包未改未删。NAS、物理手机、完整 MoviePilot/真实路径映射仍未验收。
- 最终上传扫描：219 个、0 symlink，私钥/provider token/个人 home/超大文件无命中；仅保留既有合成测试/受控本地 exec 等需审阅 flags。扫描并非秘密不存在证明；实际暂存后仍需复核。
