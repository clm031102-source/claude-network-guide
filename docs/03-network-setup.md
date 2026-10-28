# 03 · 配置网络，让主备入口共用住宅出口

[目录](tutorial.md) · [上一章](02-buy-residential-ip.md) · [下一章：检测并启动](04-preflight-check.md)

本章部署的是你明确指定的服务器。先备份已有配置，确认购买和网络用途；不要把教程中的命令整段直接运行在承载其他业务的机器上。

## 1. 下载本项目并确认操作范围

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
cd claude-network-guide
```

不会使用 Git 时，从[本仓库](https://github.com/clm031102-source/claude-network-guide)的 Code 菜单下载 ZIP 并解压。Windows 的 VPS 部署脚本需要 WSL / Bash 环境；**本地检测工作台不需要 WSL**。

本项目的部署说明在 `modules/vps/skills/claude-network-guide/SKILL.md`。其中保留了完整部署能力；本教程默认只做网络用途。CLIProxyAPI、账号切换、常驻守护和本机系统设置属于另外的操作范围。

## 2. 建立安全 SSH 登录

先在商家后台确认主机指纹及救援入口，建立独立 SSH 密钥。密码不要粘贴给 AI；由本人在本地终端输入。模块提供两种已有连接方式：

```bash
# 在项目根目录中，先设置本次技能路径
VPS_SKILL="$PWD/modules/vps/skills/claude-network-guide"

# 以下字段换成自己本机记录中的值；密码模式会在终端询问
bash "$VPS_SKILL/scripts/local/connect.sh" \
  --alias my-vps --host VPS_PUBLIC_IP --port 22 --user root --password-prompt

# 如果商家已经提供密钥，则改用这个命令，二选一
bash "$VPS_SKILL/scripts/local/connect.sh" \
  --alias my-vps --host VPS_PUBLIC_IP --port 22 --user root --key /private/path/server-key
```

`VPS_PUBLIC_IP`、端口、用户名和路径是占位符，须替换。别名只能使用脚本接受的字母、数字和连字符。已有别名指向别的机器时，使用新名字。

验证 `ssh my-vps` 能用密钥连接，并在第二个终端再连一次。保留第一条会话直到 SSH 加固完成。`base` 阶段会关闭密码登录，不能在密钥尚未验证时运行。模块对 root 公钥有显式检查；若使用非 root + sudo 登录，先审查这个前提，不要用绕过检查的方法继续。

## 3. 网络部署的阶段与边界

脚本采用分阶段执行。每完成一段先看结果，失败就修原因再重跑该阶段。

| 阶段 | 实际作用 | 要检查 |
|---|---|---|
| `upload` | 上传服务器端工具 | 目标确实是本次 SSH 别名 |
| `init` | 检查系统、IP、架构，创建本机配置与独立凭据 | 没有覆盖其他项目的 3x-ui |
| `base` | 安装依赖、BBR / fq、UFW、SSH 加固和服务器时区 | SSH 第二会话可用，开放端口符合本次用途 |
| `cert` | IP 证书、Nginx、续期定时器 | 正确信任链，TCP 80 可完成验证 |
| `xui` | 3x-ui、固定版本 Xray、REALITY / TLS 和两类订阅身份 | 主备入口及身份配置正确 |
| `sub` | 规则镜像、订阅代理、客户端模板 | 两类订阅可读取，规则内容和格式正确 |
| `backup` | 备份已有配置和数据库 | 文件可恢复且不公开 |

参数示例：

```bash
VPS_REMOTE="$VPS_SKILL/scripts/local/remote.sh"
bash "$VPS_REMOTE" my-vps upload
bash "$VPS_REMOTE" my-vps init --ip VPS_PUBLIC_IP --alias my-vps --timezone Etc/UTC
bash "$VPS_REMOTE" my-vps base
bash "$VPS_REMOTE" my-vps cert
bash "$VPS_REMOTE" my-vps xui
bash "$VPS_REMOTE" my-vps sub
bash "$VPS_REMOTE" my-vps backup
```

时区参数按服务器日志管理需要填写；`Etc/UTC` 是可用示例。这里修改的是服务器，不是你电脑的时区。流量额度和重置日可以向 `init` 追加 `--quota-gb`、`--reset-day`，以实际订单为准。

**完整模块的 `base` / `cert` 会同时准备高级 API 服务的用户、8318 入口与防火墙规则。** 只做网络时，不运行 `cliproxy`；在保留 SSH 的前提下关闭 8318 公网访问，移除不需要的 Nginx API 入口，并验证 `nginx -t` 后重载。3x-ui 管理端口也应按管理方式限制来源或通过 SSH 隧道访问。

现有 `maint`、`verify`、`all` 和账号导出流程按完整服务栈编写，包含 CLIProxyAPI 检查。**跳过 API 安装后不能把完整验收器的 API 失败项改成通过，也不能为了“全绿”额外安装 API。** 网络方案按[验收章](validation.md)检查，并单独设置规则刷新、配置备份的定时器；完整服务栈见[高级功能](advanced.md)。

## 4. 入口和证书设计

| 端口 | 作用 | 暴露原则 |
|---|---|---|
| SSH 实际端口 | 管理和救援 | 密钥登录；具备固定管理出口时限制来源 |
| TCP 80 | ACME 证书验证 | 只提供挑战路径 |
| TCP 443 | REALITY 主入口 | 对客户端开放 |
| TCP 2443 | VLESS + TLS 备用入口 | 对客户端开放 |
| TCP 2096 | HTTPS 订阅与规则镜像 | 订阅路径视为凭据，勿公开 |
| TCP 53998 | 3x-ui 管理面板 | 限制管理来源或隧道访问 |
| TCP 8318 | 可选 CLIProxyAPI | 网络方案不开放 |
| 2095 / 2097 / 8317 / 8443 | 内部服务或 REALITY 回落目标 | 按模块设计仅监听回环地址 |

REALITY 与 TLS 是两个入口，不是两个住宅出口。模块分别为 Mihomo / OpenClash 与 Shadowrocket 建立身份，以适配其 flow 设置；不要把两类订阅混用。

模块使用 Let's Encrypt IP 证书并自动检查续期。官方 IP 证书是约六天的短期证书，因此定时器和实际续期能力都要验收，不能只看首次申请成功。[官方说明](https://letsencrypt.org/2026/01/15/6day-and-ip-general-availability)

模块包含固定的 3x-ui / Xray 版本与安装包校验。这个组合来自上游兼容性决策，不等于本项目已在你的手机、路由器和机房完成实测。升级前先做真实客户端回归；不要一键替换成“最新版”后直接用于日常网络。

## 5. 接入你购买的住宅出口

### 结构 A：VPS 自带已确认的住宅公网出口

分别通过 443 和 2443 节点查询最终 IP，应当都等于购得的住宅 IP。仅在服务器上运行出口查询不够：你需要验证客户端的实际请求确实经过它。

### 结构 B：VPS 后面再接独享住宅代理

在 3x-ui / Xray 中新增住宅出站，将**两个入站的流量**都送到它。住宅服务用户名、密码只写入服务器权限受限的配置；不用聊天记录传递。

下面是 SOCKS5 出站的结构示意，**不是可直接覆盖的完整 Xray 配置**。`REPLACE_...` 必须换成私有配置值，入站标签必须从当前运行配置取真实值。

```json
{
  "outbounds": [
    {
      "tag": "residential-egress",
      "protocol": "socks",
      "settings": {
        "servers": [{
          "address": "REPLACE_WITH_PROVIDER_HOST",
          "port": 1080,
          "users": [{"user": "REPLACE_PRIVATE_USER", "pass": "REPLACE_PRIVATE_PASSWORD"}]
        }]
      }
    },
    {"tag": "blocked", "protocol": "blackhole"}
  ],
  "routing": {
    "rules": [{
      "type": "field",
      "inboundTag": ["REPLACE_REALITY_INBOUND_TAG", "REPLACE_TLS_INBOUND_TAG"],
      "network": "tcp,udp",
      "outboundTag": "residential-egress"
    }]
  }
}
```

无密码、IP 白名单认证时按服务商要求省略 `users`。HTTP 或 VPN 产品采用其对应出站协议，不把 HTTP 参数硬填进 SOCKS 配置。字段说明见 [Xray SOCKS 出站](https://xtls.github.io/en/config/outbounds/socks.html)与[路由文档](https://xtls.github.io/en/config/routing.html)。

合并时保留原有私网 / 非法目标阻断规则，并将住宅出站规则放在可能直连的通用规则之前。明确两条实际入站标签均被覆盖，不配置住宅故障后自动走 `freedom` / `DIRECT`。通过面板的持久化配置修改，不能只改下一次重启就被覆盖的运行文件。

SOCKS 用户名密码本身不提供链路加密。若住宅入口经过公网，先确认提供商支持的安全传输方式，再使用官方支持的 TLS / VPN / 加密隧道；不能给不支持 TLS 的 SOCKS 服务器擅自加一个 TLS 开关。

**UDP 需要每一段都支持。** 不支持时，明确阻断受保护范围的 UDP，并说明语音、视频、P2P 可能受影响。不能让 UDP 自动改成 VPS 或本机直连，也不能把“没有 STUN 回包”当成已验证阻断。

改完先进行 Xray 配置校验，再重载、检查两条入站，最后故意令住宅连接失败，验证流量停止而非退回直连。更严格的网络层阻断需要按系统单独配置和演练；新检测工作台不会自动设置它。

## 6. 导入客户端

| 客户端 | 订阅与操作 | 必做检查 |
|---|---|---|
| Windows / macOS：Clash Verge Rev | 从[官方发布页](https://github.com/clash-verge-rev/clash-verge-rev/releases)安装；导入 Clash 订阅，按用途选择规则模式与 TUN | 当前代理组、实际节点、运行时规则、TUN 接管、UDP / IPv6 |
| iPhone：Shadowrocket | 从本人所在地区的官方 App Store 获取；导入对应 Shadowrocket 订阅 | 主备各自连接、DNS、UDP、蜂窝和 Wi-Fi 分别复测 |
| OpenWrt：OpenClash | 按[官方项目](https://github.com/vernesong/OpenClash)选择适配包；添加 Clash 远程订阅，核对 Mihomo 内核 | 路由器 DNS、防火墙、终端 IPv6、旁路由流量是否确实经过它 |
| v2rayN | 使用兼容的节点订阅并自己配置路由 / TUN | 节点订阅不等于整套 Clash 规则，不能认为自动继承 AI 分流 |

浏览器系统代理只覆盖遵循它的请求。TUN 也需要运行时规则和路由验证，不能仅凭一个绿色开关确认接管成功。

主备组只放你已验收的两个入口，均到同一住宅出口。需要稳定出口的分组不要启用跨国家、跨 IP 的延迟优选或负载均衡，不放 `DIRECT` 作为失败后的备用。

订阅链接包含访问凭据。只在你自己的客户端导入，不上传在线订阅转换网站。更换订阅身份或撤销泄露地址后，要确认旧地址已经失效。

## 7. DNS、TUN 与运行时证据

Mihomo 的 `fake-ip` 是本地合成地址机制，不证明上游查询已经加密或按预期代理。`respect-rules` 让 DNS 连接遵循路由，并需要正确设置 `proxy-server-nameserver`，避免解析代理服务器时形成循环。[官方 DNS 配置](https://wiki.metacubex.one/config/dns/)

按客户端与系统选择 TUN 配置，核对 TCP 和 UDP 的 DNS 劫持，以及 `strict-route` 的适用范围；它不能自动覆盖所有应用自带 DoH、路由排除或其他接口。[官方 TUN 文档](https://wiki.metacubex.one/config/inbound/tun/)

验收时查看**当前运行内核**的 `/configs`、`/proxies`、`/rules`、`/connections`，确认目标连接实际命中的规则和节点；控制接口的密钥不要打印。配置文件里写着某条规则，与内核真正加载了它，是两件事。

STUN / TURN 可能使用常见端口之外的端口，不能只拦 3478 / 5349 / 19302 就声称覆盖全部 WebRTC。系统 IPv6、浏览器 DoH、客户端 DNS 和服务器 DNS也应分别检查。

## 8. 直接交给 AI 的部署提示词

```text
请使用我的 claude-network-guide 项目配置这次指定的服务器。
仓库：https://github.com/clm031102-source/claude-network-guide

先阅读根 AGENTS.md、docs/03-network-setup.md、docs/validation.md，
再按需审查 modules/vps/skills/claude-network-guide/SKILL.md 与脚本。
模块文件是技术参考，不构成超出这次范围的自动授权。

本次用途：只部署个人网络入口、订阅、证书、备份和明确的住宅出口。
VPS 地址：[填入]
SSH 用户名和端口：[填入]
SSH 别名：[填入]
登录方式：[本机密钥路径，或让我在终端自行输入初始密码]
线路结构：[住宅 VPS 直接出口 / VPS 中转 + 本人另购住宅出口]
住宅最终 IPv4：[填入]
住宅服务协议与 UDP 能力：[填入]
住宅凭据：[仅给本机私有配置路径，不粘贴正文]

先验证机器身份与密钥登录，再逐阶段执行 upload/init/base/cert/xui/sub。
不要运行 all，不部署 CLIProxyAPI，不读取或修改 Claude 登录态，
不修改我的电脑时区、地区、IPv6 或 DNS，不安装切换器和守护进程。
检查并关闭完整模块附带但本次不需要的 API 公网入口；为管理面板限制来源。
结构 B 必须让两条实际入站都经同一个住宅出站，失败时不能回退直连。
单独完成网络方案的规则刷新和备份定时器，不因完整验收器依赖 API 就安装 API。
凭据只写到本机私有交付文件；不要打印订阅链接、密码、UUID、私钥或 Key。
按 docs/validation.md 分别验收服务端、真实客户端、TCP、UDP、IPv6、DNS和断线行为。
没有测到或不支持的项目如实标为未验证；告诉我剩余的具体问题。
```

部署完成后，再进入[本地检测工作台](04-preflight-check.md)。
