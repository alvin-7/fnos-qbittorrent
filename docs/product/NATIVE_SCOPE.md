# 原生 x86_64 测试版范围与门禁

本文件取代 PRODUCT_DESIGN 中 Docker 运行、容器路径、端口直访和不加代理的旧决定；保留现有 UI、Unix gateway 无域名会话/CSRF 与 PT 默认策略。

- 交付独立应用 ID `fnos-qbittorrent-native`，版本 1.1.0（native 测试包），不是旧 `fnos-qbittorrent` 1.0.x 的覆盖升级。旧共享目录、配置、任务和镜像绝不自动修改。
- NAS 无 Docker、无 apt、无系统库覆盖。构建阶段从已校验官方 qB Docker 5.2.4-1 原料提取真正 nox 及完整私有 musl 动态依赖；显式执行私有 loader，避免宿主 glibc 版本要求。不是 GUI AppImage，也不是第三方自称官方静态构建。保留 OCI config/layer 来源与每文件 SHA，许可证和对应源代码来源清单。
- 官方下载页提供 GUI AppImage、源码，不能将 GUI 改名为 nox；官方 nox 镜像是本次可用的已落地来源。可复现构建以原料 SHA 固定，不以可变 tag 作为唯一信任。
- fnOS 包用户运行 Go 生命周期控制器、qB 和 Unix gateway。qB 仅 127.0.0.1:18080；不信任所有本机用户：关闭 auth subnet bypass，启用 LocalHostAuth，随机强密码仅包用户可读；gateway 持 qB 会话访问 backend。Host/CSRF 均保留。fnOS 统一网关为唯一主入口。
- DHT/PeX/LSD/UPnP 默认关闭；BT 监听 6881。独立应用与旧版不能同时占用 BT/控制端口，启动冲突必须报错，不杀其他进程。
- `TRIM_PKGVAR` 保存 profile/凭据，升级只替换 target。包内无运行时镜像拉取；stop 必须保存 resume；PID 校验 UID、starttime、cmdline/exec 身份并使用 pidfd 定位，限时停止，不 pkill。
- 数据迁移仅文档指导：先停旧版并备份 torrent/fastresume/conf，再用户明确选择新下载目录；旧 `/downloads` 路径不能直接导入 resume，优先原始 torrent 到 native、指定已有文件实际路径、先暂停再校验。未真机时不自动执行迁移。

## 阶段门禁
1. 源与依赖：真实 `--version`、ELF 架构/loader/dependency closure，记录 sha/许可证/源码位置。
2. 原生生命周期：start/status/stop、冲突/伪造 PID/超时/保留数据，真实 qB API v5.2.4 设置读回、添加、PT private fixture 双原生 nox 字节传输。
3. 真实 Unix socket + 浏览器 iframe 加载**包内 UI**，无域名 bootstrap/session+CSRF，拒绝伪造身份/恶意来源；Go 原有回归保留。
4. fnpack 原生包、无 docker-project/容器引用的运行脚本、文件/许可/sha 审计。
5. 待 NAS：最低 fnOS 版本、CPU 指令集/kernel/musl DNS兼容、包用户 ACL、系统网关 socket 访问、升级/重装持久化、真实 FNConnect/手机，均不得以 WSL 通过冒充真机。

官方依据（本轮实际读取）：https://developer.fnnas.com/docs/core-concepts/framework ，/privilege ，/gateway-registration ，/environment-variables 。最低 fnOS 版本尚未声明已验证；需具有当前文档所述统一网关能力。
