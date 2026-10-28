# 06 · 备份、升级与恢复

[目录](tutorial.md) · [验收](validation.md) · [高级功能](advanced.md)

先保存当前可用配置，再改下一件事。一次只换一个变量，出问题才知道该恢复什么。

## 网络方案的定时维护

`cert` 阶段已经创建证书续期定时器。`sub` 阶段安装规则刷新程序，但完整模块的 `maint` 还会启用 CLIProxyAPI 更新器。因此纯网络方案应单独安装规则与备份定时器，不运行完整 `maint`。

以下是管理员在目标服务器上创建的单元内容。创建前先检查同名服务是否存在；有现存配置时备份并合并，不覆盖其他用途。

`/etc/systemd/system/claude-network-guide-rules.service`：

```ini
[Unit]
Description=Claude Network Guide rule mirror refresh
Wants=network-online.target
After=network-online.target
[Service]
Type=oneshot
UMask=0022
ExecStart=/usr/local/sbin/xxd-vps-refresh-rules
```

`/etc/systemd/system/claude-network-guide-rules.timer`：

```ini
[Unit]
Description=Daily rule mirror refresh
[Timer]
OnCalendar=daily
RandomizedDelaySec=1800
Persistent=true
[Install]
WantedBy=timers.target
```

`/etc/systemd/system/claude-network-guide-backup.service`：

```ini
[Unit]
Description=Claude Network Guide configuration backup
[Service]
Type=oneshot
UMask=0077
ExecStart=/usr/bin/python3 /root/xxd-vps-deploy/server/xxd-vps.py backup
```

`/etc/systemd/system/claude-network-guide-backup.timer`：

```ini
[Unit]
Description=Daily configuration backup
[Timer]
OnCalendar=*-*-* 03:15:00
RandomizedDelaySec=900
Persistent=true
[Install]
WantedBy=timers.target
```

备份服务依赖当前上传路径；不得删除该目录而保留定时器。将工具迁到正式位置时，同步修改 `ExecStart` 并验证。root 执行的脚本和父目录必须由 root 控制，不能由普通用户写入。

确认文件后执行：

```bash
systemctl daemon-reload
systemctl enable --now claude-network-guide-rules.timer claude-network-guide-backup.timer
systemctl start claude-network-guide-rules.service claude-network-guide-backup.service
systemctl list-timers --all
```

这是在你明确选择的 VPS 上安装维护服务；本地工作台不会自动执行。证书、订阅和维护的内部路径部分保留上游兼容名称。

## 备份什么

模块的 `backup` 备份 3x-ui 数据库、Xray 配置、Nginx、证书、部署配置、SSH / UFW / systemd 等，保留最近 7 份；目录权限 700、文件权限 600。含有住宅凭据、订阅身份或账号文件的备份同样是秘密。

手动备份可以从本机调用：

```bash
bash "$VPS_REMOTE" my-vps backup
```

服务器本地备份不能应对磁盘或实例整体丢失。需要异地备份时，用你控制的加密存储保存，私钥和解密口令分开保管。备份本身不等于可恢复：在隔离环境演练读取、配置校验和服务恢复。

## 升级纪律

1. 记录当前版本、仓库 commit、配置和校验值，确认备份可读。
2. 先读对应项目的官方发布说明；检查系统和客户端兼容性。
3. 在测试机器或可恢复配置中验证；3x-ui / Xray 不自动追最新。
4. 维护时间内升级，保留旧二进制和旧配置。
5. 重跑主备 TCP、UDP、DNS、IPv6、证书和断线验收；失败恢复旧版本和匹配配置。

只替换二进制而不恢复配套配置，可能无法完成回滚。重新部署 `xui` 也可能影响自定义住宅出站，执行前比较配置并准备保留或重新合并。

## 常见问题

| 现象 | 优先核对 |
|---|---|
| SSH 连接失败 | 服务商控制台、实例地址、端口、主机指纹、安全组；不要反复重装系统 |
| IP 证书申请失败 | TCP 80 的外部可达性、ACME 路径、系统时间、证书客户端日志 |
| 订阅无法更新 | 2096 连接、证书、订阅路径、客户端是否误把本地隧道地址交给远端代理 |
| TCP 出口正确，UDP 不同 | 住宅服务 UDP 能力、TUN、STUN 规则、出站匹配顺序 |
| 默认通道与显式代理 IP 不同 | TUN 实际接管、系统路由、排除接口、不同代理组与监听器 |
| 主备切换后 IP 变了 | 两个入站是否到同一住宅出站，是否意外启用自动选择或 DIRECT |
| DNS 返回 fake-IP | 继续核对实际上游和连接，不能就此宣布 DNS 不泄漏 |
| 检测服务返回 429 / 超时 | 保留未知状态，稍后重新测；不要改为通过 |
| 软件升级后规则失效 | 检查当前内核运行配置和接口，不只检查磁盘文件 |

## 交给 AI 的维护提示词

```text
请按 claude-network-guide 检查我指定的服务器 ssh my-vps。
仓库：https://github.com/clm031102-source/claude-network-guide
先读 docs/validation.md、docs/maintenance.md 及实际部署记录。
本次先只检查；不要上传新工具、重启服务、升级软件或改配置。
若是网络方案，不把未部署 CLIProxyAPI 认作必须修复的问题。
查看服务、证书、定时器、规则及配置权限，敏感内容不要打印。
区分已验证、失败和未验证，并说明需要修复的具体文件与预计影响。
```

确认修复范围后，按相同 SSH 目标和最后有效版本操作。不要把“阅读新教程”当成更新或重启授权。
