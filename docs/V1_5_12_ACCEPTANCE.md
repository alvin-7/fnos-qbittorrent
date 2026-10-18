# 1.5.12 发布验收与范围

本次为正式版本号发布，不把版本号等同于 NAS/物理手机兼容性验收完成。

## 发布范围

保留产品源码、Go 单元/目录/授权/分析回归、浏览器测试与其必要构建脚本、文档、OpenDesign HTML/脚本与推广文章。排除全部 .runtime、release、evidence、源码归档、临时准备/验证目录、node_modules/dist、设计大截图及含机器路径的注册元数据。历史发布资产全部保留，不重写、不删除。

公开测试中的 example/test 域名、loopback 与明确的隔离 Docker 子网为合成 fixture，不代表真实部署地址；运行时密码由隔离程序生成，不提交凭据文件。签名 URL 测试仅使用合成值验证脱敏，不包含真实 PT 签名。

## 构建边界

`tools/build_native_1_5_12.py` 重新编译完整当前原生 UI、gateway 和 native-control，复用 SHA256 锁定的历史 1.4.8 runtime，并保留 1.5.1 对应源码材料。**NOT clean runtime rebuild**；CI 完整原生工具链闭包仍缺失。源码 bundle 仅复制公开候选 inventory 和小型有效包模板，不遍历本地临时目录。

## 已运行验收

- 当前 npm build、gateway/native 全量 Go race 与 vet：PASS。
- 状态语义、组合过滤、站点 null/empty 语义、单导航契约：PASS。
- 固定历史提交 12721ed 的 refresh 复现旧空响应覆盖问题；当前源码保留较新结果：PASS。测试固定历史基线，提交后不依赖 HEAD。
- 当前完整 UI、真实 qB 5.2.4、Unix test gateway，在 1440/390px iframe 的状态、分类/标签/站点返回、清除筛选、选择清理、陈旧空响应回归：PASS，业务 POST 为零。该权限 provider 是测试模拟，不是 NAS。

## 最终不可变 FPK 回归

最终 FPK gateway 使用生产固定官方 Unix socket，在私有 user/mount/network namespace 内对接模拟平台 provider 与真实 qB 5.2.4：PASS。两根与真实 nested tmpfs、ACL/schema/token/scope 拒绝、符号链接拒绝均通过。

最终 packaged iframe 在 1440/390/360px：工作区、分析不请求原始 Tracker、批量暂停读回、嵌套目录锁、详情/设置、四授权根、仅回填/取消、祖先导航一致性、陈旧浏览取消、手机安全计数、Unicode 长目录、tmpfs/bind 子目录、筛选返回及 600px 滚动恢复：PASS。随后四根 preferences 与暂停任务路径分别真实读回；授权拒绝零新任务；statfs 容量去重、private 聚合、connector 换密/重启/禁用重启：PASS。

本轮临时授权根在同一文件系统，容量去重为 **1 个容量域/4 根**，不是旧 harness 报告文字里的 two_volumes。独立两根 nested tmpfs 生产 gateway 测试另已通过。没有在宿主创建 /vol 根，也不把本轮声称为 exact /vol 路径或 NAS UID 验收。namespace UID 0 映射开发身份，不是 qb-native。

历史 harness 的固定卷数、exact /vol 选择器和旧 ACL 诊断 key 已在**本地 additive overlay**校正，不修改历史证据或产品，最终完整执行通过。原始失败保留本地；不得将先前 harness 失败计为产品通过。测试后文档脱敏变更与最终验收报告不在冻结 source bundle 内，须与本次 Git 提交和 hashed verification overlay 一同交付；产品源码/最终 UI/gateway 未变化。

FPK SHA256：`2cd2543d6f00582153ebd81bf5d56d4a5f993fdcbcaf6bc6554fae17b479eb9a`

Source SHA256：`b271d4399db5d954f2870726467e9ebba8be5c80b1b38298bb4fc46868828c61`

构建检查 249 个 packaged files 等于 staging；内外层 resource 的所有重复成员通过，旧 release 哈希保持不变。strip 仅作用新 staging。

## 剩余边界

- implemented_unverified：真实 NAS 下目录发现、qb-native OS/ACL/挂载身份、实际 MoviePilot 挂载路径。
- blocked：缺少现场 NAS、物理手机及完整 clean runtime rebuild 输入闭包。

目录相对祖先仅遍历修复不等于现场立即子目录读取拒绝的根因已解决。保留 NOFOLLOW、当前授权边界、每子项 ACL 与安全错误聚合；不建议 chmod 777。

## 许可证与交付

原创代码 GPL-3.0-or-later，署名 alvin-7；第三方各自许可证见 LICENSE、THIRD_PARTY_NOTICES.md 与匹配源码材料。分发 FPK 必须同时提供匹配完整 source bundle 与校验文件。Git tag 与 GitHub Release、Release 页面与实际附件是不同状态，不能相互替代。

原始运行日志和截图仅本地保留，不入 Git。仅删除本轮新建且已停止的临时验证目录；先列清单，不删除历史 release 或旧证据。
