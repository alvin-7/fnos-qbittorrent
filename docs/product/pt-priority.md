# PT 优先产品约束

- 本应用专注 PT 站任务，不将 DHT / PeX / LSD 发现网络作为零速度修复方案。运行配置应保持三者关闭；UPnP 默认关闭，不自动开启。
- 尊重种子的 `private` 标记，不重写种子、不增加公开 Tracker、不通过修改发现策略绕过站点规则。UI 的私有状态仅供诊断展示。
- 诊断顺序：真实 qB 状态、元数据、Tracker 状态/认证消息、已连接与总 seeder/peer、连接数、队列和限速、路径/磁盘错误、入站监听信息。全局 `connection_status` 不是端口可达性证明；没有测速不能凭 0 速度推断网络故障。
- Tracker URL 仅展示协议、主机及端口，隐藏路径、用户凭据和全部 query/fragment；错误消息中的 URL 同样脱敏。不得保存或使用用户真实 passkey / 签名 URL 作测试。
- 默认添加显式传 `stopped=false`；用户勾选暂停才传 `true`。HTTP/HTTPS 的完整查询参数原样交给 qB，不要求 `.torrent` 后缀。文件和 URL 使用相同停止及保存路径参数。
- 添加成功仅表示 qB 接受，异步 URL 抓取、重复、无效种子仍可能没有新任务。UI 读取任务真实 state，不把 HTTP 202 或 `pending_count` 宣称为已开始传输。
- 测试只创建独立本地容器和内部网络，使用自有 fixture。保留用户任务和下载文件，不操作 NAS。mock 参数验证与实际 qB 传输验证必须分开报告。

## 字段依据（qBittorrent 5.2.4）

官方源码 `release-5.2.4/src/webui/api/torrentscontroller.cpp`、`transfercontroller.cpp`：
- `torrents/info`：state、num_seeds/num_complete、num_leechs/num_incomplete、availability、downloaded/uploaded、dlspeed/upspeed、priority、eta。
- `torrents/properties`：has_metadata、nb_connections、seeds/seeds_total、peers/peers_total、total_downloaded_session/total_uploaded_session、total_downloaded/total_uploaded、dl_limit/up_limit、private、save_path/download_path。
- `torrents/trackers`：url、status、msg、num_seeds、num_leeches。
- `transfer/info`：dht_nodes、connection_status、dl_rate_limit/up_rate_limit。没有入站可达性测速、元数据百分比或具体磁盘错误文本。
- `torrents/add` 可能返回 HTTP 202 和 `pending_count`；文件可同步返回 `added_torrent_ids`、`success_count`、`failure_count`。不能假定所有成功均为旧版 `Ok.`。

## 业务验收

- `npx playwright test tests/business-diagnostics.spec.ts --workers=1`：mock，仅验证 UI 和请求参数。
- 启动 `npx vite --host 127.0.0.1 --port 15173` 后执行 `python tests/business_real.py`：两个新建真实 qB 5.2.4 容器，internal 网络，自有 HTTP query 种子端点，真实 UI 提交和 74-byte 校验。Chrome 使用测试专用本地透明传输代理，不测试发布网关/NAS。
- `evidence/business-real.json` 保存真实证据。HTTPS 参数透传用 mock 验证，不把它当作真实 HTTPS 站点下载证明。
