# 常见问题与修复

先看脚本 `停止：` 后面的原因，再在这里找对应条目。修好后**重跑同一个阶段**。

## 登录阶段（connect.sh）

**密码登录失败**
- 密码输错：请用户到服务商后台核对或重置 root 密码。
- 服务商要求首次登录改密码（提示 `You are required to change your password`）：请用户先用服务商后台的 VNC 控制台或自己的终端登录一次改掉密码，再用新密码重试。
- 服务器禁止了 root 密码登录：改用服务商提供的普通用户（`--user 用户名`），该用户需要能 `sudo`。

**服务商给的密钥登录不上**
- 有些服务商的密钥要先在后台"绑定"到这台服务器才生效；也有的只接受密码。请用户在后台确认，或改用密码方式。
- 压缩包里有多把私钥、是 PuTTY 的 `.ppk`、或私钥带口令：请用户下载 OpenSSH 格式、不带口令的私钥，或改用密码方式。

**macOS 读不到"下载"文件夹里的密钥**：系统隐私保护拦截了终端，请用户把文件拖到桌面，再给新路径。

**ssh 名称已被占用**：`~/.ssh/config` 里同名条目指向了别的服务器。换一个名称，不要改动原条目。

**密码登录成功，但密钥登录报 `Permission denied (password)`**：服务商的系统镜像在 `sshd_config` 里写了 `PubkeyAuthentication no`（括号里只列出 password，说明服务器根本不接受密钥）。connect.sh 用密码登录时会自动检测并改成 `yes`（原文件备份为 `sshd_config.bak-xxd-pubkey`，`sshd -t` 检查通过才重载）。登录用户不是 root 时改不了，请用户在服务商后台把它打开。

**服务商后台重装系统后，原来的 ssh 名称连不上**：重装会换主机密钥，SSH 端口也可能变。先 `ssh-keygen -R IP`（非 22 端口用 `ssh-keygen -R "[IP]:端口"`）删掉旧主机密钥；端口变了就把 `~/.ssh/config` 里这个名称那一段的 `Port` 改成新端口（connect.sh 看到名称已存在且 IP 相同时不会改写配置），再用新密码重跑 connect.sh。

## init

- **公网 IP 不是用户给的 IP**：连错了服务器，或者 IP 抄错了。停下来和用户核对，不要加参数强行继续。
- **检测到已有 3x-ui 数据库**：这台机器装过别的面板。如果用户确认这是刚买的机器、上面没有要保留的东西，请他在服务商后台把系统重装为 Ubuntu 24.04 LTS，再从 connect 开始。
- **系统不支持**：只支持 Ubuntu 22.04+ / Debian 12+。请用户在后台重装系统，搬瓦工开通时的默认系统多半就是这种情况。搬瓦工的步骤：KiwiVM 首页点 Stop 关机 → 左侧 Install new OS → 选 Ubuntu 24.04（x86_64）→ 勾选同意 → Reload → 几分钟后页面显示新 root 密码和 SSH 端口（只显示一次，让用户抄下）→ 状态回到 Running（没有就点 Start）。其他商家在服务器详情页找 Reinstall / Rebuild。图文版：<https://github.com/clm031102-source/claude-network-guide/blob/main/modules/vps/site/src/pages/howto/reinstall-os.mdx>。重装后按上面"重装系统后连不上"一条清旧主机密钥，再用新密码重跑 connect.sh。

## cert：IP 证书申请失败

1. 服务商有安全组 / 防火墙面板时，确认已放行 **TCP 80**（以及 443、2443、2096、8318、53998）。
2. 在用户电脑上测 `curl -sS -m 10 -o /dev/null -w '%{http_code}\n' http://IP/.well-known/acme-challenge/test`：返回 404 说明 80 端口通了。
3. Let's Encrypt 对同一 IP 有频率限制，短时间内失败多次时要等一段时间再试。
4. 不要改用自签名证书，也不要关掉客户端的证书校验。

## xui

- **3x-ui 面板没有在 HTTPS 53998 上响应**：`journalctl -u x-ui -n 50` 看原因。常见是证书路径不对（先确认 cert 阶段通过）或 53998 被其他程序占用（`ss -lntp | grep 53998`）。
- **生成的 Xray 配置不符合预期**：说明某个入口或身份缺失、flow 不对。重跑 `xui`，脚本会补齐缺的入口并重新挂好身份。

## sub

- **规则下载不完整**：服务器暂时访问不了 GitHub。过几分钟重跑 `sub`；已经下载成功的文件会保留。
- **订阅里的规则与本机镜像不一致**：某个上游改了文件格式。把 `files/clash-template.yaml` 里对应规则集的 `behavior` 改成实际格式（`domain` / `ipcidr` / `classical`），重跑 `xui` 和 `sub`。
- **更新了 skill 之后想让老服务器用上新规则**：先 `upload`，再重跑 `sub`。`sub` 会把新模板写进 3x-ui，只重载订阅服务，节点不断线；客户端下次更新订阅就生效。
- **微信图片发不出去 / 一直转圈**：确认订阅里有 `IP-ASN,132203,DIRECT` 这一条（老部署按上一条重跑 `sub`），客户端更新订阅后重启微信。

## 客户端

**导入订阅后连不上**
1. Clash 类客户端用 **Clash 订阅**，Shadowrocket 用 **Shadowrocket 订阅**，不要混用。
2. 在同一订阅里换另一个节点（Reality ↔ TLS）试试。
3. 确认客户端版本较新（Clash Verge Rev 用最新版；旧的 Clash for Windows 不支持 Reality）。
4. 在服务器上跑 `xxd-vps verify`，看节点结构那一项是否 PASS。

**Clash for Windows 报 `yaml: unmarshal errors ... cannot unmarshal !!seq into string`**：客户端太旧，不支持 Mihomo 的配置字段。改用 Clash Verge Rev。

**检测网站提示 WebRTC 泄露，UDP 出口是国内 IP**：Clash Verge 只开了系统代理。系统代理只接管 TCP，浏览器 WebRTC 的 UDP 直接从本地出去。改开「虚拟网卡模式」（TUN），Windows 再开「严格路由」；Clash 设置里的「IPv6」保持开启（Clash Verge 用它覆盖订阅里的 `ipv6: false`，关掉后 IPv6 会绕过虚拟网卡）。节点本身支持 UDP（订阅里 `udp: true`），STUN 实测出口就是服务器 IP。不要用禁用或限制 WebRTC 的扩展代替。完整步骤、检测命令和故障表见仓库 `docs/Clash-Verge-WebRTC泄露修复手册.md`。

**国内连不上（超时），国外网络正常**
- 先在用户电脑上测：`curl -sS -o /dev/null -w '%{http_code}\n' --max-time 10 https://IP:2096/`。超时说明用户的网络到这个 IP 不通，与配置无关。
- 分别用 Wi-Fi、手机流量、不同运营商测试。只有某个运营商不通，多半是线路问题。
- 这种情况换配置、换域名都解决不了，只能联系服务商换 IP 或换线路更好的套餐。

**速度比别人慢很多**
- 先确认单位：Fast.com 显示 Mbps，下载工具常显示 MB/s（1 MB/s ≈ 8 Mbps）。
- 用同一台设备、同一网络、只切换节点来比较。
- 检查本地链路：Wi-Fi 是否 5 GHz、网线 / 路由器 LAN 口是否掉到百兆（`ethtool` 或路由器后台看协商速率）、路由器 CPU 是否跑满。
- 服务器侧：`ssh 名称 'sysctl -n net.ipv4.tcp_congestion_control'` 应显示 `bbr`。

**Google Play 里的应用一直「等待中」或更新失败**：多半是国行手机。Play 给国行手机分配北京、上海、广州的 Google 缓存节点（`rr*---sn-2x3|ni5|j5o*****.xn--ngstr-lra8j.com`，也有 `gvt1.com`、`googlevideo.com`、`xn--ngstr-cn-8za9o.com`），这些节点从境外服务器连不上（TCP 通、TLS 握手无回应），必须国内直连。新模板用一条 `DOMAIN-REGEX` 让它们直连。旧服务器先 `upload` 再重跑 `sub`（`sync_clash_rules` 写入新模板，只 SIGHUP 3x-ui，Xray 不断线），客户端更新订阅。**不要让用户切「全局」模式**，那样这些节点也走代理，更连不上。排查时看客户端「连接」页：更新时出现 `sn-2x3`/`sn-ni5`/`sn-j5o` 的地址走代理并超时，就是这个原因；海外版系统的手机走 Google 海外节点，不受影响。

**浏览器打开订阅地址提示"不是私密连接"**：证书不对或过期。`ssh 名称 'xxd-vps verify'` 看证书项；如果续期失败，查 `journalctl -u xxd-vps-cert-renew`，通常是 80 端口被安全组拦了。

**OpenClash 里 AI 网站很慢或解析超时**：订阅给 AI 域名配置了 1.1.1.1 / 8.8.8.8 的 DoH，并靠 `respect-rules` 让这些查询走代理。OpenClash 会强制关闭 `respect-rules`，查询就变成直连海外 DoH，在部分网络会超时（Clash Verge Rev 不受影响）。遇到时，在 OpenClash 的配置覆写里删掉这些 AI 域名的 `nameserver-policy` 条目，只保留 `rule-set:cn-domain`。

## CLIProxyAPI

- **管理中心打得开但调用模型失败 / 模型列表为空**：还没添加上游账号或供应商 Key，这是正常的。
- **内存紧张**：`systemctl show cli-proxy-api -p MemoryCurrent`，`journalctl -k --since '24 hours ago' | grep -i oom`。1 GB 内存的机器建议升级到 2 GB；不要给服务加 `MemoryMax`。
- **自动更新情况**：`journalctl -u cliproxy-auto-update -n 30`；状态文件 `/var/lib/cliproxy-auto-update/last-run.json`。看到 `ROLLBACK verified` 表示新版本没通过健康检查，已经自动换回旧版。

## 什么时候不要动手

- 用户没要求的其他服务器、路由器、`~/.ssh/config` 里的其他条目。
- 3x-ui / Xray 的版本：除非已经在测试机上用真实客户端验证过新版本。

## 修不好的时候

如实告诉用户卡在哪一项、影响是什么，不要为了"解决"去重装服务器。如果原因是教程没写清楚或脚本有 bug，建议用户到 GitHub 提 Issue（<https://github.com/clm031102-source/claude-network-guide/issues>），附上报错文字；截图里的 IP、订阅地址和密码先打码。
