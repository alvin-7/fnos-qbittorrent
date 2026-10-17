# 1.4.8 strip 本地发行与验证

## 范围与不可变性

新增 `tools/build_native_1_4_8.py`，以不可变 1.4.7 FPK 为运行时输入，重新构建当前源码的 native UI/gateway。历史 `build_native_1_4_1.py` 文件名虽旧、内容为 1.4.7，已恢复为 Git 原样，不用于本次构建。不改产品行为、NAS、真实任务或凭据。

最终 staging 的 `qbittorrent-nox`、`gateway`、`native-control` 均调用 `strip --strip-debug`，没有对 qB/native-control 使用 strip-all。Go gateway 另用 `go build -trimpath -ldflags '-s -w'`。继承的 native-control 未重新编译，只移除调试信息。最终三个 ELF 与 FPK 中对应文件逐字节一致。

**这是包体/磁盘占用优化，不保证 RSS 下降。** DWARF 通常是非加载段；未进行 RSS 前后对比，不能由 FPK 大小推断内存、速度或下载性能改善。gateway 在已经 `-s -w` 后再 strip-debug 从 6,291,608 增至 6,292,088 bytes，保留这一真实结果，不把每一步都描述为缩小。

## 实测体积（bytes）

| 项目 | 1.4.7 | 1.4.8 |
|---|---:|---:|
| FPK | 38,403,677 | 33,622,282 |
| qbittorrent-nox | 19,041,208 | 19,027,288 |
| gateway | 9,219,527 | 6,292,088 |
| native-control | 8,497,587 | 6,245,040 |

FPK 减少 4,781,395 bytes（12.45%）。qB 原有 `.debug_aranges/.debug_info/.debug_abbrev/.debug_line/.debug_frame/.debug_str/.debug_line_str/.debug_loclists/.debug_rnglists` 已移除；native-control 原有压缩 DWARF `.debug_abbrev/.debug_line/.debug_frame/.debug_gdb_scripts/.debug_info/.debug_loc/.debug_ranges` 已移除。gateway 在 strip-debug 前已由 Go linker 移除 DWARF。完整前后 `readelf -SW` 输出保留在本地 `evidence/strip-1.4.8.json`。

## 已执行通过（verified）

- `npm run build`（构建器两次 native 编译成功）。
- `GO111MODULE=off go test -race ./gateway ./native`、`go vet ./gateway ./native`。
- selection140、label_batch130、labels130、connector134_validation 四个 Node 回归。
- FPK 249 个 app 普通文件逐字节匹配 staging；manifest 唯一新增 fnpack checksum，验证其为 app.tgz MD5；当前 native 转换后 dist/public/private 与包一致，gateway 转换后源码与当前源码一致；对应源码包 SHA256 与包内 manifest 一致。
- 审计执行时，构建前记录的历史 release 普通文件 SHA256 全部再读一致。后续提交前复核发现历史文件（包括 1.4.7）已从 release 消失；本流程未执行删除/移动，原因未确认。不得把早先通过解释为当前历史存储仍完整；需由工作区所有者核对其他并发清理/归档。1.4.8 产物仍完整。
- 最终 qB 5.2.4 经内置 musl loader 实际运行、受保护 API 登录读取成功；私有、无发现的本地双进程传输 4,194,304 bytes，核对文件字节；强制/暂停/普通开始、队列、限速持久化和真实定时 0→1→0 回读通过。
- 最终 gateway + UI 在 1440/390 宽 iframe 通过任务操作、设置/分享率、分类标签批量读回、无重放及拒绝未授权请求；受控无效种子、URL/文件/磁力反馈通过。
- 最终 native-control `prepare/start/status/stop` 均退出 0，停止后 status 为 3；仅操作新建本地 fixture。

可审计本地证据：`evidence/strip148-artifact-verification.json`、`pt148-real.json`、`pt148-browser.json`、`selection148-browser.json`、`selection148-real-readback.json`、`strip148-native-control-smoke.json` 及 `.runtime/strip148-verification-v2.log`。原始材料遵循现有 ignore 规则不入 Git，公开此摘要和可复用检查入口 `tools/verify_strip_1_4_8.py`。校验入口会创建独立新工作目录，已有验证目录时拒绝覆盖。

最初审计严格逐字节比较 manifest 被 fnpack 添加的 checksum 正确阻止，已改为校验 checksum + 其余行一致并在新目录完成全套测试。没有修改 FPK 规避失败。

## 不可变交付与源码补充

FPK：`fnos-qbittorrent-native-1.4.8-x86_64.fpk`

SHA256：`660bb88a300d1bce43384480067fbb72ab7190d662c52ca375a4a15896ce7676`

完整对应源码基础包：`native-1.4.8-source-bundle.tar.gz`

SHA256：`6e54f2616a8aa5b9d626c660e7437564bb7a890bc5e2325a173a799a064f1854`

构建冻结后新增了验证 harness、此证据说明、README 和构建前历史哈希自动记录；它们没有改变运行时代码/UI/gateway。基础源码包不覆盖重打；最终文本/工具另存 `native-1.4.8-verification-overlay-v2.tar.gz`，其 SHA256 在同名 `.sha256`。此 overlay 只补充文本工具，不能替代完整对应源码包。FPK、完整基础源码包、overlay 都保留本地 release，按现有 `.gitignore` 不上传巨大二进制；Git 跟踪精简说明与脚本。

## 未验收边界（blocked / unverified）

没有执行 NAS 安装/升级/卸载、物理手机或真实 MoviePilot 路径映射；本次未重跑 Docker 客户端完整连接矩阵与完整外部发行合规验收。手机宽度 iframe 不等于物理手机。包仍是本地候选，不因 strip 或这些通过项成为 production-ready。外发必须遵守包内许可证/NOTICE、完整对应源码配套交付要求。

构建入口依赖本地历史 FPK、完整源材料、fnpack、strip/readelf，不能从空 checkout 重建完整 qB 运行时；输出存在时拒绝覆盖，不要删除旧包为重跑腾位置。
